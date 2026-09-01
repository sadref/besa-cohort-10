# Week 02 - Agentic AI with AWS Serverless

## Overview
This module demonstrates how to build production-grade, asynchronous multi-agent systems using AWS Serverless architectures. It explores two foundational coordination patterns for enterprise AI agents: **Choreography** (event-driven using Amazon EventBridge) and **Orchestration** (workflow-managed using AWS Step Functions).

The core scenario implements an intelligent Travel Booking Workflow composed of multiple specialized Lambda agents (Planner, Flight Manager, Weather, and Hotel Agents) interacting with Amazon Bedrock.

---

## Workshop Reference
* **Official Workshop**: [Building Agentic AI architectures with AWS Serverless](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/en-US/workshop)

---

## Architecture & Coordination Patterns

### 1. Choreography Pattern (Event-Driven)
* **Mechanism**: Agents communicate asynchronously through Amazon EventBridge events (e.g., `FinalBookingCompleted`, `HotelRecommendationsReady`).
* **Components**: AWS Lambda, Amazon EventBridge, Amazon Bedrock Agent, Amazon SNS.
* **Key Benefit**: High decoupling, independent agent execution, and resilient event routing.

### 2. Orchestration Pattern (Workflow State Machine)
* **Mechanism**: Centralized control managed deterministically by an AWS Step Functions state machine.
* **Components**: AWS Step Functions, AWS Lambda, Amazon Bedrock.
* **Key Benefit**: Clear visual state tracking, built-in error handling/retries, and end-to-end execution history.

---

## Directory Structure

```text
week-02-agentic-serverless/
├── README.md                                   # Documentation for Week 2
├── travel-booking-orchestration.json           # Step Functions State Machine definition
├── high-risk-booking.json                     # Test payload for edge-case scenarios
├── hotel-agent/                                # Custom Bedrock-integrated Hotel Agent
│   └── lambda_function.py
├── planner-agent/                              # Main Travel Planner Agent
│   ├── lambda_function.py
│   └── requirements.txt
└── exported_agents/                            # Exported Lambda Agents from AWS Workshop
    ├── merged-multi-agent-workshop-flight-manager-agent/
    ├── merged-multi-agent-workshop-hotel-agent/
    ├── merged-multi-agent-workshop-planner-agent/
    ├── merged-multi-agent-workshop-weather-agent/
    ├── orchestration-multi-agent-workshop-orch-flight-manager-agent/
    ├── orchestration-multi-agent-workshop-orch-planner-agent/
    └── orchestration-multi-agent-workshop-orch-weather-agent/