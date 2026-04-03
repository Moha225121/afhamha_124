import httpx
import os

RESALA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL2Rldi5yZXNhbGEubHkiLCJzdWIiOiI3OTlkYjg4Ny01NTkzLTRlYzAtOWZlMC1iYjJiODM3ZmQ3NWYiLCJpYXQiOjE3NzUyMzUxOTYsImp0aSI6IjZjZThiZmFjLWRhODktNGM5Ni1iNjVkLTI3M2MzZThhNTllYyJ9.1BfZ9lGRXOasLdzw_Tsa_QIfoPcLEVsO1WxNx57aDRI"

def send_otp(phone, service_name="Afhamha"):
    """
    Sends an OTP to the given phone number using Resala API.
    Returns the pin if successful, None otherwise.
    """
    # Clean phone number (remove spaces)
    phone = phone.strip().replace(" ", "")
    
    # Ensure phone is in international format (e.g., 2189...)
    if phone.startswith("0") and len(phone) >= 9:
        phone = "218" + phone[1:]
    elif not phone.startswith("218") and len(phone) >= 8:
        phone = "218" + phone
        
    url = f"https://dev.resala.ly/api/v1/pins?service_name={service_name}&len=4"
    headers = {
        "Authorization": f"Bearer {RESALA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "phone": phone
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload, timeout=10.0)
            if response.status_code in [200, 201]:
                response_data = response.json()
                return response_data.get("pin")
            else:
                print(f"Resala API Error: Status {response.status_code}, Body {response.text}")
                return None
    except Exception as e:
        print(f"Exception calling Resala API: {e}")
        return None
