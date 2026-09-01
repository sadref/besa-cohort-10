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
Orchestration Flight Manager Agent - Searches and books flights
Returns structured JSON for Step Functions orchestration
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List
from strands import Agent, tool, ToolContext
from strands.models.bedrock import BedrockModel

# Environment variables
STACK_NAME = os.environ.get('STACK_NAME', 'workshop')
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-2')

class FlightTools:
    """Tools for flight search and booking"""
    
    def __init__(self, booking_id: str):
        self.booking_id = booking_id
    
    @tool(name="search_flights", context=True)
    def search_flights(self, origin: str, destination: str, travel_date: str, budget: float, travelers: int, tool_context: ToolContext) -> Dict[str, Any]:
        """Search for available flights within budget"""
        print(f"[tool]   bookingID={self.booking_id} SearchFlights -> {{ origin: {origin}, dest: {destination}, date: {travel_date}, budget: {budget}, travelers: {travelers} }}")
        
        # Simulate flight search results
        base_flights = [
            {
                'airline': 'American',
                'flight': 'AA678',
                'price_per_person': 450,
                'departure': '08:40',
                'arrival': '16:20',
                'duration': '4h 40m',
                'rating': 4.0
            },
            {
                'airline': 'United',
                'flight': 'UA234', 
                'price_per_person': 420,
                'departure': '15:15',
                'arrival': '22:55',
                'duration': '4h 40m',
                'rating': 3.9
            },
            {
                'airline': 'Delta',
                'flight': 'DL567',
                'price_per_person': 480,
                'departure': '21:25',
                'arrival': '05:05+1',
                'duration': '4h 40m',
                'rating': 4.2
            }
        ]
        
        # Calculate total costs and filter by budget
        available_flights = []
        for flight in base_flights:
            total_cost = flight['price_per_person'] * travelers
            if total_cost <= budget:
                flight_option = flight.copy()
                flight_option['total_cost'] = total_cost
                flight_option['savings'] = budget - total_cost
                available_flights.append(flight_option)
        
        result = {
            'flights_found': len(available_flights),
            'available_flights': available_flights,
            'search_criteria': {
                'origin': origin,
                'destination': destination,
                'date': travel_date,
                'budget': budget,
                'travelers': travelers
            },
            'all_within_budget': len(available_flights) > 0
        }
        
        print(f"[tool]   bookingID={self.booking_id} SearchFlights <- {{ flights_found: {len(available_flights)}, status: success }}")
        return result
    
    @tool(name="select_best_flight", context=True)
    def select_best_flight(self, available_flights: List[Dict], criteria: str, tool_context: ToolContext) -> Dict[str, Any]:
        """Select the best flight based on criteria (price, rating, schedule)"""
        print(f"[tool]   bookingID={self.booking_id} SelectBestFlight -> {{ flights: {len(available_flights)}, criteria: {criteria} }}")
        
        if not available_flights:
            return {'error': 'No flights available'}
        
        # Selection logic based on criteria
        if 'price' in criteria.lower() or 'budget' in criteria.lower():
            best_flight = min(available_flights, key=lambda x: x['total_cost'])
            reason = 'Best value - lowest price'
        elif 'rating' in criteria.lower() or 'quality' in criteria.lower():
            best_flight = max(available_flights, key=lambda x: x['rating'])
            reason = 'Highest rated airline'
        else:
            # Default to best value
            best_flight = min(available_flights, key=lambda x: x['total_cost'])
            reason = 'Best value - lowest price with reasonable schedule'
        
        result = {
            'selected_flight': best_flight,
            'selection_reason': reason,
            'alternatives_count': len(available_flights) - 1
        }
        
        print(f"[tool]   bookingID={self.booking_id} SelectBestFlight <- {{ airline: {best_flight['airline']}, cost: {best_flight['total_cost']} }}")
        return result
    
    @tool(name="book_flight", context=True)
    def book_flight(self, flight_details: Dict, travelers: int, payment_info: Dict, tool_context: ToolContext) -> Dict[str, Any]:
        """Book the selected flight"""
        print(f"[tool]   bookingID={self.booking_id} BookFlight -> {{ airline: {flight_details.get('airline')}, cost: {flight_details.get('total_cost')} }}")
        
        # Generate booking confirmation
        confirmation_number = f"{flight_details.get('airline', 'XX')[:2].upper()}{str(uuid.uuid4())[:6].upper()}"
        
        result = {
            'booking_confirmed': True,
            'confirmation_number': confirmation_number,
            'flight_details': flight_details,
            'total_cost': flight_details.get('total_cost', 0),
            'booking_timestamp': datetime.utcnow().isoformat(),
            'passenger_count': travelers
        }
        
        print(f"[tool]   bookingID={self.booking_id} BookFlight <- {{ confirmed: True, confirmation: {confirmation_number} }}")
        return result

def handle_search_action(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle flight search request"""
    booking_id = event.get('bookingID', 'unknown')
    origin = event.get('origin', 'Unknown')
    destination = event.get('destination', 'Unknown')
    travel_dates = event.get('travel_dates', {})
    travelers_data = event.get('travelers', 1)
    # Handle both integer and object formats for travelers
    if isinstance(travelers_data, dict):
        travelers = travelers_data.get('adults', 0) + travelers_data.get('children', 0)
    else:
        travelers = travelers_data
    budget = event.get('budget', 1000)
    airline_preference = event.get('airline_preference', 'Any')
    
    print(f"[action] bookingID={booking_id} Search flights for {origin} → {destination}")
    
    # Create agent with flight tools
    tools = FlightTools(booking_id)
    model = BedrockModel(model_id="global.anthropic.claude-sonnet-4-6")
    agent = Agent(
        agent_id="flight-searcher",
        name="flight-manager-agent",
        model=model,
        system_prompt="Search for flights and provide recommendations based on budget, schedule, and airline preferences.",
        tools=[tools.search_flights, tools.select_best_flight]
    )
    
    # Build flight search prompt
    # Handle both formats: {start, end} and {departure, return}
    start_date = travel_dates.get('start') or travel_dates.get('departure', 'unknown')
    
    search_prompt = f"""
    Search for flights for booking {booking_id}:
    
    - Route: {origin} to {destination}
    - Travel Date: {start_date}
    - Travelers: {travelers}
    - Budget: ${budget}
    - Airline Preference: {airline_preference}
    
    Find available flights within budget and recommend the best option.
    Consider price, schedule, and airline rating in your recommendation.
    """
    
    response = agent(search_prompt)
    
    # Simulate flight search results
    flight_options = [
        {
            'airline': 'American',
            'flight': 'AA678',
            'total_cost': 900,
            'departure': '08:40',
            'arrival': '16:20',
            'rating': 4.0
        },
        {
            'airline': 'United',
            'flight': 'UA234',
            'total_cost': 840,
            'departure': '15:15',
            'arrival': '22:55',
            'rating': 3.9
        },
        {
            'airline': 'Delta',
            'flight': 'DL567',
            'total_cost': 960,
            'departure': '21:25',
            'arrival': '05:05+1',
            'rating': 4.2
        }
    ]
    
    # Filter flights within budget
    within_budget_flights = [f for f in flight_options if f['total_cost'] <= budget]
    
    # Select best option (lowest cost)
    best_option = min(within_budget_flights, key=lambda x: x['total_cost']) if within_budget_flights else None
    
    return {
        'statusCode': 200,
        'flights_found': len(within_budget_flights),
        'flight_options': within_budget_flights,
        'best_option': best_option,
        'within_budget': len(within_budget_flights) > 0,
        'agent_response': str(response)
    }

def handle_book_action(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle flight booking request"""
    booking_id = event.get('bookingID', 'unknown')
    selected_flight = event.get('selected_flight', {})
    travelers = event.get('travelers', 1)
    payment_info = event.get('payment_info', {})
    
    print(f"[action] bookingID={booking_id} Book flight {selected_flight.get('airline', 'unknown')} {selected_flight.get('flight', 'unknown')}")
    
    # Create agent with booking tools
    tools = FlightTools(booking_id)
    model = BedrockModel(model_id="global.anthropic.claude-sonnet-4-6")
    agent = Agent(
        agent_id="flight-booker",
        name="flight-manager-agent",
        model=model,
        system_prompt="Process flight bookings and generate confirmation details.",
        tools=[tools.book_flight]
    )
    
    # Build booking prompt
    booking_prompt = f"""
    Process flight booking for booking ID {booking_id}:
    
    Flight Details:
    {json.dumps(selected_flight, indent=2)}
    
    Travelers: {travelers}
    Payment Approved: {payment_info.get('approved', False)}
    
    Complete the booking and generate confirmation details.
    """
    
    response = agent(booking_prompt)
    
    # Generate booking confirmation
    confirmation_number = f"{selected_flight.get('airline', 'XX')[:2].upper()}{str(uuid.uuid4())[:6].upper()}"
    
    return {
        'statusCode': 200,
        'booking_confirmation': {
            'confirmation_number': confirmation_number,
            'flight_details': selected_flight,
            'passenger_details': {
                'count': travelers,
                'booking_id': booking_id
            }
        },
        'confirmation_number': confirmation_number,
        'total_cost': selected_flight.get('total_cost', 0),
        'booking_status': 'confirmed',
        'agent_response': str(response)
    }

def lambda_handler(event, context):
    """Main Lambda handler for orchestration flight manager agent"""
    try:
        print(f"Orchestration Flight Manager Agent received event: {json.dumps(event)}")
        
        action = event.get('action', 'search')
        
        if action == 'search':
            return handle_search_action(event)
        elif action == 'book':
            return handle_book_action(event)
        else:
            return {
                'statusCode': 400,
                'error': f'Unknown action: {action}',
                'message': 'Supported actions: search, book'
            }
            
    except Exception as e:
        print(f"Error in Orchestration Flight Manager Agent: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'error': str(e),
            'message': 'Orchestration flight manager agent error'
        }