import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_strategic_narrative(context_data: dict) -> dict:
    """
    Sends simulation data to OpenAI and returns a structured strategic review.
    """
    
    # 1. The Persona (Who the AI is)
    system_prompt = """
        You are a Senior Infrastructure Economist advising the Provincial Treasury.
            
            Your task is two-fold:
            1. Analyze specific graph data points (Condition Forecast, Financials).
            2. Write a formal strategic conclusion.

            Output Format: return ONLY a JSON object with this exact structure:
            {
                "chart_insights": {
                    "condition_forecast": "One short, sharp sentence analyzing the VCI trend (e.g. 'The rapid decline in 2028 indicates a structural failure point.').",
                    "budget_impact": "One short, sharp sentence on the financial reality (e.g. 'Current funding covers only 60% of depreciation.')."
                },
                "executive_summary": "A 2-sentence high-level summary of the crisis.",
                "risk_analysis": "A paragraph explaining the financial and engineering risks.",
                "economic_impact": "A short statement on broader economic effects.",
                "recommended_action": ["Action 1", "Action 2", "Action 3"]
            }
    """

    # 2. The Data (What the AI analyzes)
    user_prompt = f"""
    Analyze the following network simulation results for a funding proposal:
    
    - Project Name: {context_data.get('project_name', 'Provincial Road Network')}
    - Forecast Duration: {context_data.get('duration')} Years
    - Current Asset Value (CRC): {context_data.get('current_asset_value')}
    - Current Network Health (VCI): {context_data.get('start_vci')}
    
    SCENARIO OUTCOME (If this budget is approved):
    - Total Budget Required (NPV): {context_data.get('total_cost')}
    - Future Network Health (VCI): {context_data.get('end_vci')}
    - Health Change: {context_data.get('vci_change')} points
    - Inflation Rate Used: {context_data.get('inflation')}%
    
    If the VCI drops, emphasize the destruction of asset value. 
    If the VCI improves, emphasize the return on investment.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Or "gpt-3.5-turbo" if you want to save credits
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}, # Forces clean JSON
            temperature=0.7
        )
        
        # Parse the JSON string back into a Python dictionary
        content = response.choices[0].message.content
        return json.loads(content)
        
    except Exception as e:
        print(f"OpenAI Error: {e}")
        # Fallback if API fails or runs out of credits
        return {
            "executive_summary": "Unable to generate AI analysis at this time.",
            "risk_analysis": "Please review the data manually.",
            "economic_impact": "N/A",
            "recommended_action": ["Review inputs", "Check API connection"]
        }