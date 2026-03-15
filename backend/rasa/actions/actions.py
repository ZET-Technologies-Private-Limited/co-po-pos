"""
Rasa Custom Actions Server
Integrates with LangGraph workflows and FastAPI services
"""
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormAction
from rasa_sdk.events import SlotSet, FollowupAction
import requests
import json
import asyncio
import aiohttp

# Configuration
FASTAPI_BASE_URL = "http://localhost:8000/api/v1"
LANGGRAPH_BASE_URL = "http://localhost:8001"

class ActionStartCoGeneration(Action):
    def name(self) -> Text:
        return "action_start_co_generation"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        course_id = tracker.get_slot("course_id")
        
        # Check if COs already exist
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{FASTAPI_BASE_URL}/courses/{course_id}/outcomes") as resp:
                if resp.status == 200:
                    cos = await resp.json()
                    if cos:
                        dispatcher.utter_message(
                            text=f"Course {course_id} already has {len(cos)} COs. "
                                 "Would you like to regenerate them?"
                        )
                        return []
        
        dispatcher.utter_message(
            text="Let's generate Course Outcomes! Please provide your course syllabus."
        )
        return []

class ActionParseSyllabus(Action):
    def name(self) -> Text:
        return "action_parse_syllabus"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        syllabus_text = tracker.get_slot("syllabus_parsed")
        course_id = tracker.get_slot("course_id")
        
        # Call LangGraph syllabus parsing workflow
        async with aiohttp.ClientSession() as session:
            payload = {
                "course_id": course_id,
                "syllabus_text": syllabus_text
            }
            async with session.post(f"{LANGGRAPH_BASE_URL}/workflows/parse_syllabus", 
                                  json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    parsed_syllabus = result.get("parsed_syllabus")
                    
                    dispatcher.utter_message(
                        text=f"I've analyzed your syllabus and found {len(parsed_syllabus.get('units', []))} units. "
                             "Now I'll load the Program Outcomes for mapping."
                    )
                    return [SlotSet("syllabus_parsed", parsed_syllabus)]
                else:
                    dispatcher.utter_message(
                        text="Sorry, I couldn't parse the syllabus. Please try again."
                    )
                    return []

class ActionGenerateCos(Action):
    def name(self) -> Text:
        return "action_generate_cos"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        course_id = tracker.get_slot("course_id")
        syllabus_parsed = tracker.get_slot("syllabus_parsed")
        po_list = tracker.get_slot("po_list")
        pso_list = tracker.get_slot("pso_list")
        co_count = int(tracker.get_slot("co_count") or 5)
        
        # Call LangGraph CO generation workflow
        async with aiohttp.ClientSession() as session:
            payload = {
                "course_id": course_id,
                "syllabus": syllabus_parsed,
                "program_outcomes": po_list,
                "program_specific_outcomes": pso_list,
                "num_cos": co_count
            }
            
            async with session.post(f"{LANGGRAPH_BASE_URL}/workflows/generate_cos", 
                                  json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    cos_draft = result.get("course_outcomes", [])
                    
                    co_text = "\n".join([
                        f"**{co['code']}** ({co['bloom_level']}): {co['statement']}"
                        for co in cos_draft
                    ])
                    
                    dispatcher.utter_message(
                        text=f"I've generated {len(cos_draft)} Course Outcomes:\n\n{co_text}\n\n"
                             "Do these look good? You can approve them, edit specific ones, or regenerate."
                    )
                    
                    return [SlotSet("current_co_draft", cos_draft)]
                else:
                    dispatcher.utter_message(
                        text="Sorry, I couldn't generate COs. Please try again."
                    )
                    return []

class ActionSaveCos(Action):
    def name(self) -> Text:
        return "action_save_cos"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        course_id = tracker.get_slot("course_id")
        co_draft = tracker.get_slot("current_co_draft")
        
        # Save COs via FastAPI
        async with aiohttp.ClientSession() as session:
            payload = {
                "course_id": course_id,
                "course_outcomes": co_draft
            }
            
            async with session.post(f"{FASTAPI_BASE_URL}/cos/save", 
                                  json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    
                    dispatcher.utter_message(
                        text=f"✅ Successfully saved {len(co_draft)} Course Outcomes! "
                             "CO-PO mappings have also been created. "
                             "You can now configure exams or upload marks."
                    )
                    
                    return [
                        SlotSet("current_co_draft", None),
                        SlotSet("syllabus_parsed", None)
                    ]
                else:
                    dispatcher.utter_message(
                        text="Sorry, I couldn't save the COs. Please try again."
                    )
                    return []

class ActionAnalyseQuestion(Action):
    def name(self) -> Text:
        return "action_analyse_question"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        question_text = tracker.get_slot("question_under_analysis")
        course_id = tracker.get_slot("course_id")
        
        # Call LangGraph question analysis workflow
        async with aiohttp.ClientSession() as session:
            payload = {
                "question_text": question_text,
                "course_id": course_id
            }
            
            async with session.post(f"{LANGGRAPH_BASE_URL}/workflows/analyze_question", 
                                  json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    bt_level = result.get("bt_level")
                    suggested_co = result.get("suggested_co")
                    confidence = result.get("confidence")
                    explanation = result.get("explanation")
                    
                    dispatcher.utter_message(
                        text=f"**Question Analysis:**\n"
                             f"Bloom's Level: **{bt_level.upper()}**\n"
                             f"Suggested CO: **{suggested_co}**\n"
                             f"Confidence: {confidence:.1%}\n\n"
                             f"Explanation: {explanation}"
                    )
                    
                    return [SlotSet("question_under_analysis", question_text)]
                else:
                    dispatcher.utter_message(
                        text="Sorry, I couldn't analyze the question. Please try again."
                    )
                    return []

class ActionExplainAttainment(Action):
    def name(self) -> Text:
        return "action_explain_attainment"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        course_id = tracker.get_slot("course_id")
        co_number = tracker.get_slot("co_number")
        
        # Call LangGraph attainment explanation workflow
        async with aiohttp.ClientSession() as session:
            payload = {
                "course_id": course_id,
                "co_number": co_number
            }
            
            async with session.post(f"{LANGGRAPH_BASE_URL}/workflows/explain_attainment", 
                                  json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    explanation = result.get("explanation")
                    calculation_steps = result.get("calculation_steps")
                    suggestions = result.get("suggestions", [])
                    
                    response_text = f"**CO{co_number} Attainment Explanation:**\n\n{explanation}\n\n"
                    
                    if calculation_steps:
                        response_text += "**Calculation Steps:**\n"
                        for step in calculation_steps:
                            response_text += f"• {step}\n"
                    
                    if suggestions:
                        response_text += "\n**Improvement Suggestions:**\n"
                        for suggestion in suggestions:
                            response_text += f"• {suggestion}\n"
                    
                    dispatcher.utter_message(text=response_text)
                    
                    return [SlotSet("last_attainment_query", f"CO{co_number}")]
                else:
                    dispatcher.utter_message(
                        text="Sorry, I couldn't explain the attainment. Please try again."
                    )
                    return []