MEDICAL_KEYWORDS = [ 
    "symptom","pain","fever","medicine","doctor","disease", 
    "treatment","diagnosis","drug","dosage","infection", 
    "surgery","hospital","prescription","allergy","chronic", 
    "blood","heart","lung","kidney","diabetes","cancer", 
    "headache","cough","nausea","vomit","diarrhea","rash", 
    "injury","fracture","anxiety","depression","mental", 
    "vitamin","tablet","capsule","vaccine","ache","swelling" 
] 
 
def quick_check(text: str) -> bool: 
    lower = text.lower() 
    for kw in MEDICAL_KEYWORDS: 
        if kw in lower: 
            return True 
    return False 
 
async def llm_classify(text: str, co_client) -> bool: 
    prompt = f"Is this query about medical or health topics? Reply ONLY 'YES' or 'NO'.\nQuery: {text}" 
    response = co_client.chat( 
        model="command-a-03-2025", 
        messages=[{"role": "user", "content": prompt}], 
        temperature=0, 
        max_tokens=5 
    ) 
    answer = response.message.content[0].text.strip().upper() 
    return "YES" in answer 
 
async def is_medical(text: str, co_client) -> bool: 
    quick = quick_check(text) 
    if quick: 
        return True 
    return await llm_classify(text, co_client) 
