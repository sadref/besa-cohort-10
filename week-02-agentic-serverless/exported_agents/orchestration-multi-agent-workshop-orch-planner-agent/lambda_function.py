#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Orchestration Planner Agent - Coordinates travel booking workflow
Handles both extraction and analysis/booking phases
"""

import json
import os
import uuid
import boto3
from datetime import datetime
from typing import Dict, Any
from strands import Agent, tool, ToolContext
from strands.session.s3_session_manager import S3SessionManager
from strands.models.bedrock import BedrockModel

# Environment variables
STACK_NAME = os.environ.get('STACK_NAME', 'workshop')
SESSION_BUCKET = os.environ.get('SESSION_BUCKET', 'default-session-bucket')
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-2')

def get_session_manager(booking_id: str) -> S3SessionManager:
    """Get S3 session manager for the booking"""
    return S3SessionManager(
        session_id=booking_id,
        bucket=SESSION_BUCKET,
        prefix="orchestration-sessions/",
        region_name=AWS_REGION
    )

class PlannerTools:
    """Tools for orchestration planner agent"""
    
    def __init__(self, booking_id: str):
        self.booking_id = booking_id
    
    @tool(name="extract_travel_details", context=True)
    def extract_travel_details(self, user_request: str, tool_context: ToolContext) -> Dict[str, Any]:
        """Extract and validate travel details from user request"""
        print(f"[tool]   bookingID={self.booking_id} ExtractTravelDetails -> {{ request_length: {len(user_request)} }}")
        
        result = {
            'extracted': True,
            'confidence': 'high',
            'ready_for_coordination': True,
            'validation_passed': True
        }
        
        print(f"[tool]   bookingID={self.booking_id} ExtractTravelDetails <- {{ extracted: {result['extracted']}, confidence: {result['confidence']} }}")
        return result
    
    @tool(name="analyze_booking_data", context=True)
    def analyze_booking_data(self, weather_data: Dict, flight_data: Dict, tool_context: ToolContext) -> Dict[str, Any]:
        """Analyze weather and flight data to make booking decision"""
        print(f"[tool]   bookingID={self.booking_id} AnalyzeBookingData -> {{ weather_risk: {weather_data.get('risk_level', 'unknown')}, flights_found: {flight_data.get('flights_found', 0)} }}")
        
        # Determine risk level based on weather and flight data
        weather_risk = weather_data.get('risk_level', 'LOW')
        flights_found = flight_data.get('flights_found', 0)
        within_budget = flight_data.get('within_budget', True)
        
        # Decision logic
        if weather_risk == 'HIGH' or not within_budget or flights_found == 0:
            decision = 'needs_human_review'
            reason = f"High risk detected: weather={weather_risk}, within_budget={within_budget}, flights_available={flights_found > 0}"
        else:
            decision = 'approve_booking'
            reason = f"Low risk scenario: weather={weather_risk}, budget_ok={within_budget}, flights_available={flights_found > 0}"
        
        result = {
            'decision': decision,
            'reason': reason,
            'risk_assessment': {
                'weather_risk': weather_risk,
                'budget_risk': 'LOW' if within_budget else 'HIGH',
                'availability_risk': 'LOW' if flights_found > 0 else 'HIGH'
            }
        }
        
        print(f"[tool]   bookingID={self.booking_id} AnalyzeBookingData <- {{ decision: {result['decision']}, reason: {result['reason']} }}")
        return result
    
    @tool(name="book_selected_flight", context=True)
    def book_selected_flight(self, flight_option: Dict, travelers: int, tool_context: ToolContext) -> Dict[str, Any]:
        """Book the selected flight option"""
        print(f"[tool]   bookingID={self.booking_id} BookSelectedFlight -> {{ airline: {flight_option.get('airline', 'unknown')}, cost: {flight_option.get('total_cost', 0)} }}")
        
        # Generate booking confirmation
        confirmation_number = f"CONF-{str(uuid.uuid4())[:8].upper()}"
        
        result = {
            'booking_confirmed': True,
            'confirmation_number': confirmation_number,
            'total_cost': flight_option.get('total_cost', 0),
            'flight_details': flight_option,
            'booking_timestamp': datetime.utcnow().isoformat()
        }
        
        print(f"[tool]   bookingID={self.booking_id} BookSelectedFlight <- {{ confirmed: {result['booking_confirmed']}, confirmation: {confirmation_number} }}")
        return result

def handle_planner_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle all planner requests - create agent once and let it decide"""
    booking_id = event.get('bookingID', str(uuid.uuid4()))
    
    print(f"[action] bookingID={booking_id} Processing planner request")
    
    # Create unified planner agent with rich system prompt
    tools = PlannerTools(booking_id)
    session_manager = get_session_manager(booking_id)
    model = BedrockModel(model_id="global.anthropic.claude-sonnet-4-6")
    agent = Agent(
        agent_id="planner-coordinator",
        name="planner-agent",
        model=model,
        system_prompt="""You are an intelligent travel booking planner. Analyze the incoming JSON data and determine what phase you're in:

PHASE 1 - EXTRACT: Basic travel request (origin, destination, dates, budget)
- Use extract_travel_details tool to validate the request
- Return: {"statusCode": 200, "extractedData": {...}, "confidence": "high", "ready_for_coordination": true}

PHASE 2 - ANALYZE & DECIDE: Weather + flight data provided
- Use analyze_booking_data tool to assess risks
- If LOW risk + flights available + within budget: auto-approve with booking_confirmation
- If HIGH risk OR no flights OR over budget: require human review
- Return: {"statusCode": 200, "decision": "booked|needs_human_review", "decision_reason": "...", "booking_status": "auto_approved|pending_review", "booking_confirmation": {...}|null}

PHASE 3 - FINALIZE: Human approval provided
- Use book_selected_flight tool to complete booking
- Return: {"statusCode": 200, "booking_status": "completed", "booking_confirmation": {...}}

Always include [reason] logs explaining your decisions. Maintain context across all interactions.""",
        tools=[tools.extract_travel_details, tools.analyze_booking_data, tools.book_selected_flight],
        session_manager=session_manager
    )
    
    # Just throw the raw JSON at the agent - let it figure out what to do
    prompt = f"""
Process this travel booking request:

{json.dumps(event, indent=2)}

Analyze the data structure and determine which phase this is, then take appropriate action.
"""
    
    print(f"[reason] bookingID={booking_id} Sending raw event data to intelligent planner agent")
    response = agent(prompt)
    print(f"[reason] bookingID={booking_id} Agent completed processing: {str(response)[:200]}...")
    
    # Let the agent's response guide the return format
    return parse_agent_response(event, response)

def parse_agent_response(event: Dict[str, Any], response) -> Dict[str, Any]:
    """Parse agent response and return appropriate format"""
    booking_id = event.get('bookingID', 'unknown')
    
    # Fallback response structure with all required fields
    result = {
        'statusCode': 200,
        'message': 'Request processed successfully',
        'booking_confirmation': None
    }
    
    # Determine phase and add appropriate fields based on event structure
    if event.get('weather_data') and event.get('flight_data'):
        # Analyze phase - add decision fields
        weather_data = event.get('weather_data', {})
        flight_data = event.get('flight_data', {})
        
        weather_risk = weather_data.get('risk_level', 'LOW')
        flights_found = flight_data.get('flights_found', 0)
        within_budget = flight_data.get('within_budget', True)
        
        print(f"[reason] bookingID={booking_id} Decision factors: weather_risk={weather_risk}, flights_found={flights_found}, within_budget={within_budget}")
        
        if weather_risk == 'HIGH' or not within_budget or flights_found == 0:
            result.update({
                'decision': 'needs_human_review',
                'decision_reason': f'High risk detected: weather={weather_risk}, within_budget={within_budget}, flights_available={flights_found > 0}',
                'booking_status': 'pending_review',
                'message': 'Human review required based on risk analysis'
            })
            print(f"[reason] bookingID={booking_id} Requiring human review due to risk factors")
        else:
            # Auto-approve
            best_option = flight_data.get('best_option', {})
            confirmation_number = f"CONF-{str(uuid.uuid4())[:8].upper()}"
            result.update({
                'decision': 'booked',
                'decision_reason': f'Low risk scenario: weather={weather_risk}, budget_ok={within_budget}',
                'booking_status': 'auto_approved',
                'message': 'Booking auto-approved based on analysis',
                'booking_confirmation': {
                    'confirmation_number': confirmation_number,
                    'total_cost': best_option.get('total_cost', 0),
                    'flight_details': best_option,
                    'booking_timestamp': datetime.utcnow().isoformat()
                }
            })
            print(f"[reason] bookingID={booking_id} Auto-approved booking with confirmation {confirmation_number}")
            
            # --- EVENTBRIDGE ESEMÉNY KÜLDÉSE (ÚJ RÉSZ) ---
            try:
                eb = boto3.client('events')
                eb.put_events(
                    Entries=[{
                        'Source': 'workshop.planner-agent',
                        'DetailType': 'FinalBookingCompleted',
                        'Detail': json.dumps({
                            "bookingID": booking_id,
                            "userId": event.get('userId'),
                            "origin": event.get('origin'),
                            "destination": event.get('destination'),
                            "travel_dates": event.get('travel_dates'),
                            "travelers": event.get('travelers'),
                            "budget": event.get('budget'),
                            "selected_flight": best_option
                        }),
                        'EventBusName': 'orchestration-multi-agent-workshop-event-bus'
                    }]
                )
                print(f"[eventbridge] bookingID={booking_id} FinalBookingCompleted event sent")
            except Exception as eb_err:
                print(f"[eventbridge-error] Failed to send event: {str(eb_err)}")
                
    elif event.get('human_approval'):
        # Finalize phase
        flight_data = event.get('flight_data', {})
        best_option = flight_data.get('best_option', {})
        confirmation_number = f"CONF-{str(uuid.uuid4())[:8].upper()}"
        
        result.update({
            'booking_status': 'completed',
            'booking_confirmation': {
                'confirmation_number': confirmation_number,
                'total_cost': best_option.get('total_cost', 0),
                'flight_details': best_option,
                'booking_timestamp': datetime.utcnow().isoformat()
            },
            'message': 'Booking completed successfully'
        })
        print(f"[reason] bookingID={booking_id} Finalized booking with human approval, confirmation {confirmation_number}")
        
    else:
        # Extract phase
        result.update({
            'extractedData': {
                'origin': event.get('origin'),
                'destination': event.get('destination'),
                'travel_dates': event.get('travel_dates'),
                'travelers': event.get('travelers'),
                'budget': event.get('budget'),
                'airline_preference': event.get('airline_preference')
            },
            'confidence': 'high',
            'ready_for_coordination': True
        })
        print(f"[reason] bookingID={booking_id} Extracted and validated travel request data")
    
    return result

def lambda_handler(event, context):
    """Main Lambda handler for orchestration planner agent"""
    try:
        print(f"Orchestration Planner Agent received event: {json.dumps(event)}")
        
        # Use unified planner that determines action based on incoming data
        return handle_planner_request(event)
            
    except Exception as e:
        print(f"Error in Orchestration Planner Agent: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return expected structure even on error to prevent ASL failures
        return {
            'statusCode': 500,
            'decision': 'needs_human_review',
            'decision_reason': f'System error occurred: {str(e)}',
            'booking_status': 'error',
            'booking_confirmation': None,
            'extractedData': None,
            'confidence': 'low',
            'ready_for_coordination': False,
            'error': str(e),
            'message': 'Orchestration planner agent error'
        }

