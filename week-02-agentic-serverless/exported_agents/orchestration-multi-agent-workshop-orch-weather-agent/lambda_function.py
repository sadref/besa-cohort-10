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
Orchestration Weather Agent - Analyzes weather conditions for travel dates
Returns structured JSON for Step Functions orchestration
"""

import json
import os
import random
from datetime import datetime
from typing import Dict, Any
from strands import Agent, tool, ToolContext
from strands.models.bedrock import BedrockModel

# Environment variables
STACK_NAME = os.environ.get('STACK_NAME', 'workshop')
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-2')

class WeatherTools:
    """Tools for weather analysis"""
    
    def __init__(self, booking_id: str):
        self.booking_id = booking_id
    
    @tool(name="get_weather_forecast", context=True)
    def get_weather_forecast(self, destination: str, travel_date: str, tool_context: ToolContext) -> Dict[str, Any]:
        """Get weather forecast for destination and travel date"""
        print(f"[tool]   bookingID={self.booking_id} GetWeatherForecast -> {{ destination: {destination}, date: {travel_date} }}")
        
        # Simulate weather data based on destination
        weather_scenarios = {
            'Miami': {
                'temperature': 80,
                'conditions': 'thunderstorms' if 'March' in travel_date or '03-' in travel_date else 'sunny',
                'humidity': 85,
                'wind_speed': '20 mph' if 'March' in travel_date or '03-' in travel_date else '10 mph'
            },
            'Seattle': {
                'temperature': 55,
                'conditions': 'rainy',
                'humidity': 70,
                'wind_speed': '15 mph'
            },
            'Phoenix': {
                'temperature': 95,
                'conditions': 'sunny',
                'humidity': 20,
                'wind_speed': '5 mph'
            }
        }
        
        # Default weather for unknown destinations
        weather = weather_scenarios.get(destination, {
            'temperature': 70,
            'conditions': 'partly cloudy',
            'humidity': 60,
            'wind_speed': '10 mph'
        })
        
        result = {
            'destination': destination,
            'travel_date': travel_date,
            'forecast': weather,
            'data_source': 'weather_service_api'
        }
        
        print(f"[tool]   bookingID={self.booking_id} GetWeatherForecast <- {{ conditions: {weather['conditions']}, temp: {weather['temperature']} }}")
        return result
    
    @tool(name="assess_weather_risk", context=True)
    def assess_weather_risk(self, weather_forecast: Dict, tool_context: ToolContext) -> Dict[str, Any]:
        """Assess travel risk based on weather conditions"""
        print(f"[tool]   bookingID={self.booking_id} AssessWeatherRisk -> {{ conditions: {weather_forecast.get('forecast', {}).get('conditions', 'unknown')} }}")
        
        conditions = weather_forecast.get('forecast', {}).get('conditions', 'unknown')
        temperature = weather_forecast.get('forecast', {}).get('temperature', 70)
        wind_speed = weather_forecast.get('forecast', {}).get('wind_speed', '0 mph')
        
        # Risk assessment logic
        risk_level = 'LOW'
        potential_impacts = []
        
        if 'thunderstorm' in conditions.lower() or 'severe' in conditions.lower():
            risk_level = 'HIGH'
            potential_impacts.extend(['Flight delays', 'Turbulence', 'Possible diversions'])
        elif 'rain' in conditions.lower() or 'snow' in conditions.lower():
            risk_level = 'MEDIUM'
            potential_impacts.extend(['Minor delays', 'Wet conditions'])
        elif temperature > 100 or temperature < 20:
            risk_level = 'MEDIUM'
            potential_impacts.append('Extreme temperatures')
        
        if int(wind_speed.split()[0]) > 25:
            risk_level = 'HIGH' if risk_level != 'HIGH' else 'HIGH'
            potential_impacts.append('High winds')
        
        result = {
            'risk_level': risk_level,
            'potential_impacts': potential_impacts,
            'assessment_factors': {
                'conditions': conditions,
                'temperature': temperature,
                'wind_speed': wind_speed
            }
        }
        
        print(f"[tool]   bookingID={self.booking_id} AssessWeatherRisk <- {{ risk_level: {risk_level}, impacts: {len(potential_impacts)} }}")
        return result

def handle_analyze_action(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle weather analysis for travel destination and dates"""
    booking_id = event.get('bookingID', 'unknown')
    origin = event.get('origin', 'Unknown')
    destination = event.get('destination', 'Unknown')
    travel_dates = event.get('travel_dates', {})
    
    print(f"[action] bookingID={booking_id} Analyze weather for {origin} → {destination}")
    
    # Create agent with weather tools
    tools = WeatherTools(booking_id)
    model = BedrockModel(model_id="global.anthropic.claude-sonnet-4-6")
    agent = Agent(
        agent_id="weather-analyzer",
        name="weather-agent",
        model=model,
        system_prompt="Analyze weather conditions for travel destinations and assess risks for flight travel.",
        tools=[tools.get_weather_forecast, tools.assess_weather_risk]
    )
    
    # Build weather analysis prompt
    # Handle both formats: {start, end} and {departure, return}
    start_date = travel_dates.get('start') or travel_dates.get('departure', 'unknown')
    end_date = travel_dates.get('end') or travel_dates.get('return', 'unknown')
    
    weather_prompt = f"""
    Analyze weather conditions for travel booking {booking_id}:
    
    - Destination: {destination}
    - Travel Period: {start_date} to {end_date}
    - Origin: {origin}
    
    Get the weather forecast for the destination and assess any risks for air travel.
    Focus on conditions that could impact flights like storms, high winds, or extreme weather.
    """
    
    response = agent(weather_prompt)
    
    # Simulate weather analysis results based on destination
    if 'Miami' in destination and ('March' in start_date or '03-' in start_date):
        # High risk scenario for Miami in March
        return {
            'statusCode': 200,
            'weather_analysis': {
                'destination_weather': {
                    'temperature': 80,
                    'conditions': 'thunderstorms',
                    'humidity': 85,
                    'wind_speed': '20 mph'
                },
                'travel_period': f"{start_date} to {end_date}",
                'analysis_summary': 'High risk weather conditions expected during travel period'
            },
            'risk_level': 'HIGH',
            'conditions': 'thunderstorms',
            'recommendation': 'Consider alternative travel dates due to severe weather conditions',
            'agent_response': str(response)
        }
    else:
        # Low risk scenario for other destinations/dates
        return {
            'statusCode': 200,
            'weather_analysis': {
                'destination_weather': {
                    'temperature': 72,
                    'conditions': 'partly cloudy',
                    'humidity': 60,
                    'wind_speed': '10 mph'
                },
                'travel_period': f"{start_date} to {end_date}",
                'analysis_summary': 'Favorable weather conditions expected during travel period'
            },
            'risk_level': 'LOW',
            'conditions': 'partly cloudy',
            'recommendation': 'Weather conditions are favorable for travel',
            'agent_response': str(response)
        }

def lambda_handler(event, context):
    """Main Lambda handler for orchestration weather agent"""
    try:
        print(f"Orchestration Weather Agent received event: {json.dumps(event)}")
        
        action = event.get('action', 'analyze')
        
        if action == 'analyze':
            return handle_analyze_action(event)
        else:
            return {
                'statusCode': 400,
                'error': f'Unknown action: {action}',
                'message': 'Supported actions: analyze'
            }
            
    except Exception as e:
        print(f"Error in Orchestration Weather Agent: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return expected structure even on error to prevent ASL failures
        return {
            'statusCode': 500,
            'weather_analysis': {
                'destination_weather': {
                    'temperature': 70,
                    'conditions': 'unknown',
                    'humidity': 60,
                    'wind_speed': '10 mph'
                },
                'travel_period': 'unknown',
                'analysis_summary': 'Weather analysis failed - assuming HIGH risk for safety'
            },
            'risk_level': 'HIGH',
            'conditions': 'unknown',
            'recommendation': 'Weather analysis failed - recommend human review',
            'error': str(e),
            'message': 'Orchestration weather agent error'
        }