from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from sqlalchemy.orm import Session
from typing import Optional, List
from io import BytesIO
from pypdf import PdfReader

from src.config.database import get_db
from src.models.user import User, UserMode, ConfirmationMode
from src.utils.llm_client import LLMClient

router = APIRouter()
llm_client = LLMClient()

def validate_mode(mode: str) -> UserMode:
    try:
        return UserMode(mode)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode: '{mode}'. Must be 'internship' or 'job'."
        )

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_or_update_profile(
    request: Request,
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    content_type = request.headers.get("content-type", "")
    
    user_data = {}
    master_profile = {}
    
    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON format")
            
        name = body.get("name")
        email = body.get("email")
        if not name or not email:
            raise HTTPException(status_code=400, detail="Name and Email are required")
            
        mode_str = body.get("mode", "job")
        mode = validate_mode(mode_str)
        
        confirmation_mode_str = body.get("confirmation_mode", "batch")
        try:
            confirmation_mode = ConfirmationMode(confirmation_mode_str)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid confirmation_mode: '{confirmation_mode_str}'")
            
        weekly_quota = body.get("weekly_quota", 50)
        
        # Gather all other fields for master_profile
        master_profile = {k: v for k, v in body.items() if k not in ["name", "email", "mode", "confirmation_mode", "weekly_quota"]}
        
        user_data = {
            "name": name,
            "email": email,
            "mode": mode,
            "confirmation_mode": confirmation_mode,
            "weekly_quota": weekly_quota,
            "master_profile": master_profile
        }
        
    elif "multipart/form-data" in content_type:
        if not file:
            raise HTTPException(status_code=400, detail="No file uploaded")
            
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
            
        try:
            pdf_bytes = await file.read()
            pdf_reader = PdfReader(BytesIO(pdf_bytes))
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read PDF file: {str(e)}")
            
        if not text.strip():
            raise HTTPException(status_code=400, detail="PDF file appears to be empty or unreadable")
            
        # Extract structured profile data via LLM
        try:
            extracted_data = llm_client.extract_profile(text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM Profile extraction failed: {str(e)}")
            
        name = extracted_data.get("name") or file.filename.split(".")[0]
        # In a real app we might extract email, otherwise generate placeholder if missing
        email = extracted_data.get("email") or f"extracted_{name.lower().replace(' ', '_')}@example.com"
        
        # Read optional form values or use defaults
        form_data = await request.form()
        mode_str = form_data.get("mode", "job")
        mode = validate_mode(mode_str)
        
        confirmation_mode_str = form_data.get("confirmation_mode", "batch")
        try:
            confirmation_mode = ConfirmationMode(confirmation_mode_str)
        except ValueError:
            confirmation_mode = ConfirmationMode.batch
            
        weekly_quota = int(form_data.get("weekly_quota", 50))
        
        user_data = {
            "name": name,
            "email": email,
            "mode": mode,
            "confirmation_mode": confirmation_mode,
            "weekly_quota": weekly_quota,
            "master_profile": extracted_data
        }
    else:
        raise HTTPException(
            status_code=415,
            detail="Unsupported Media Type. Must be 'application/json' or 'multipart/form-data'."
        )
        
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data["email"]).first()
    if existing_user:
        existing_user.name = user_data["name"]
        existing_user.mode = user_data["mode"]
        existing_user.confirmation_mode = user_data["confirmation_mode"]
        existing_user.weekly_quota = user_data["weekly_quota"]
        existing_user.master_profile = user_data["master_profile"]
        db.commit()
        db.refresh(existing_user)
        return existing_user
        
    # Create new user
    new_user = User(
        name=user_data["name"],
        email=user_data["email"],
        mode=user_data["mode"],
        confirmation_mode=user_data["confirmation_mode"],
        weekly_quota=user_data["weekly_quota"],
        master_profile=user_data["master_profile"]
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/{user_id}")
def get_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")
    return user
