import logging
import time
from typing import Dict, Any, TypedDict, Optional
from langgraph.graph import StateGraph, END
from ml_detection import AnomalyDetectorEnsemble
from actions import ActionSimulator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    event_data: Dict[str, Any]
    ml_analysis: Dict[str, Any]
    root_cause: Optional[str]
    selected_action: Optional[str]
    action_result: Optional[str]
    processing_time_ms: Optional[float]

class ReasoningAgent:
    """
    Reasoning Layer using LangGraph.
    State Machine Workflow: Detect -> Assess -> Diagnose -> Act
    """
    def __init__(self):
        self.ml_engine = AnomalyDetectorEnsemble()
        self.action_module = ActionSimulator(human_in_loop=True)
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Define Nodes
        workflow.add_node("detect", self.detect_node)
        workflow.add_node("assess", self.assess_node)
        workflow.add_node("diagnose", self.diagnose_node)
        workflow.add_node("act", self.act_node)

        # Define Edges
        workflow.set_entry_point("detect")
        
        def route_after_detect(state: AgentState):
            if state.get("ml_analysis", {}).get("is_anomaly", False):
                return "assess"
            return END

        workflow.add_conditional_edges("detect", route_after_detect, {"assess": "assess", END: END})
        workflow.add_edge("assess", "diagnose")
        workflow.add_edge("diagnose", "act")
        workflow.add_edge("act", END)

        return workflow.compile()

    def detect_node(self, state: AgentState):
        logger.info("Node: Detect")
        event = state["event_data"]
        analysis = self.ml_engine.predict(event)
        return {"ml_analysis": analysis}

    def assess_node(self, state: AgentState):
        logger.info("Node: Assess")
        analysis = state["ml_analysis"]
        confidence = analysis.get("confidence", 0)
        logger.info(f"Anomaly assessed with {confidence*100}% confidence.")
        return {}

    def diagnose_node(self, state: AgentState):
        logger.info("Node: Diagnose")
        event = state["event_data"]
        
        cpu = event.get("cpu_usage", 0)
        mem = event.get("memory_usage", 0)
        lat = event.get("latency", 0)
        err = event.get("error_rate", 0)
        
        root_cause = "Unknown Anomaly Pattern"
        selected_action = "none"
        
        # Logic replicating Context-Aware Root Cause Analysis
        if cpu > 85 and mem > 85:
            root_cause = "Server Overload"
            selected_action = "auto_scale"
        elif lat > 500 and err > 0.05:
            root_cause = "Service Degradation or Network Failure"
            selected_action = "restart_service"
        elif err > 0.5:
            root_cause = "Suspicious Activity / Potential Fraud"
            selected_action = "block_transaction"

        logger.info(f"Diagnosed Root Cause: {root_cause} -> Selected Action: {selected_action}")
        return {"root_cause": root_cause, "selected_action": selected_action}

    def act_node(self, state: AgentState):
        logger.info("Node: Act")
        action = state["selected_action"]
        context = {
            "root_cause": state["root_cause"],
            "event": state["event_data"]
        }
        res = self.action_module.execute_action(action, context)
        return {"action_result": res}

    def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processes a single event, tracks resolution time, and returns the final state."""
        start_time = time.time()
        initial_state = {
            "event_data": event_data,
            "ml_analysis": {},
            "root_cause": None,
            "selected_action": None,
            "action_result": None,
            "processing_time_ms": 0.0
        }
        
        result = self.graph.invoke(initial_state)
        
        end_time = time.time()
        result["processing_time_ms"] = (end_time - start_time) * 1000.0
        
        if result["ml_analysis"].get("is_anomaly"):
             logger.info(f"Resolution completed in {result['processing_time_ms']:.2f} ms (<60 seconds threshold).")
             
        return result

if __name__ == "__main__":
    agent = ReasoningAgent()
    # Mock Event: Server Overload
    logger.info("Testing Anomaly Event")
    res = agent.process_event({"cpu_usage": 95, "memory_usage": 95, "latency": 1500, "error_rate": 0.1})
    print("Final State:", res)
