import time
import json
import logging
import os
from kafka_ingestion import DataStreamConsumer
from reasoning_agent import ReasoningAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger("SystemOrchestrator")

LOG_FILE = "system_events.json"

def main():
    logger.info("Starting Autonomous Anomaly Detection & Response System")
    
    # Initialize components
    logger.info("Initializing Data Stream Consumer...")
    consumer = DataStreamConsumer()
    
    logger.info("Initializing Reasoning Agent (ML Detect -> Assess -> Diagnose -> Act)...")
    agent = ReasoningAgent()
    
    # Clear old logs
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
        
    logger.info("Pipeline Ready. Listening for real-time streams (<60s target resolution)...")
    
    try:
        for event in consumer.consume_events():
            # Process event end-to-end
            result_state = agent.process_event(event)
            
            # Format output for dashboard
            dashboard_entry = {
                "timestamp": event["timestamp"],
                "cpu_usage": event["cpu_usage"],
                "memory_usage": event["memory_usage"],
                "latency": event["latency"],
                "error_rate": event["error_rate"],
                "is_anomaly": result_state["ml_analysis"].get("is_anomaly", False),
                "confidence": result_state["ml_analysis"].get("confidence", 0.0),
                "root_cause": result_state.get("root_cause"),
                "selected_action": result_state.get("selected_action"),
                "action_result": result_state.get("action_result"),
                "processing_time_ms": result_state.get("processing_time_ms", 0.0)
            }
            
            with open(LOG_FILE, 'a') as f:
                f.write(json.dumps(dashboard_entry) + "\n")
                
            logger.info(f"Analyzed event in {dashboard_entry['processing_time_ms']:.2f} ms")
            if dashboard_entry['is_anomaly']:
                 logger.warning(f"ACTION TAKEN: {dashboard_entry['selected_action']} | RESULT: {dashboard_entry['action_result']}")
            logger.info("-" * 50)
            
    except KeyboardInterrupt:
        logger.info("System Shutting Down.")

if __name__ == "__main__":
    main()
