# Para retornar o genero:
# "SELECT * FROM Gender WHERE GenderID = 1"

# Para retornar insurance:
# 

# API
from fastapi import FastAPI
import uvicorn
# DATABASE
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
# Classes
from pydantic import BaseModel
from datetime import datetime, date

DB_INFO = "mysql+pymysql://admin:turmalrs1234@terraform-20241028192601220800000001.cv0ucuyse8jo.us-east-1.rds.amazonaws.com:3306/saudeplusdb"

engine = create_engine(DB_INFO, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
app = FastAPI()


# Para usar na criacao de dados

# Verificar userID
class Patient(BaseModel):
    Name: str
    DateOfBirth: date
    GenderID: int
    ContactNumber: str
    Email: str
    Address: str
    HealthInsuranceID: int


# Verificar ClinicID
class Appointment(BaseModel):
    PatientID: int
    DoctorID: int
    DoctorClinicID: int
    AppointmentDateTime: datetime
    AppointmentStatusID: int
    ReasonForVisit: str
    DoctorNotes: str
    CheckInStatus: bool
    TreatmentID: int


# GENDER VERIFICAR
def get_gender(gender_id):
    db_session = SessionLocal()
    result = db_session.execute(text(f"SELECT * FROM Gender WHERE GenderID = {gender_id}"))
    results = result.fetchall()
    gender = results[0][1] # Transformar [(ID, NOME)]
    
    return(gender)


# GET PATIENT BY ID
@app.get("/patient/{patient_id}")
async def get_patient(patient_id: int):
    db_session = SessionLocal()

    try:
        result = db_session.execute(text("SELECT * FROM Patient WHERE PatientID = :patient_id"), {"patient_id": patient_id})
        results = result.fetchone()

        # Codigo para adicionar o Genero como texto
        results = dict(results)
        gender = get_gender(results["GenderID"])
        results["Gender"] = gender 

        return {"status": "success", "data": results}

    #except:
    #    return {"status": "error", "message": "Patient not found"}
    except Exception as e:
        return {"status": "error", "message": f"Error retrieving patient: {str(e)}"}

@app.get("/patients")
async def get_patients():
    db_session = SessionLocal()

    try:
        result = db_session.execute(text("SELECT * FROM Patient"))
        results = result.fetchall()

        patients_list = [dict(row) for row in results]

        return {"status": "success", "data": patients_list}

    except Exception as e:
        return {"status": "error", "message": f"Error retrieving patients: {str(e)}"}
    
# CREATE PATIENT
@app.post("/create_patient")
async def create_patient(item: Patient):
    db_session = SessionLocal()

    try:
        db_session.execute(
            text("INSERT INTO Patient (Name, DateOfBirth, GenderID, ContactNumber, Email, Address, HealthInsuranceID) VALUES (:Name, :DateOfBirth, :GenderID, :ContactNumber, :Email, :Address, :HealthInsuranceID)"),
            {
                "Name": item.Name,
                "DateOfBirth": item.DateOfBirth,
                "GenderID": item.GenderID,
                "ContactNumber": item.ContactNumber,
                "Email": item.Email,
                "Address": item.Address,
                "HealthInsuranceID": item.HealthInsuranceID 
            }
        )
        db_session.commit()

        return {"status": "success", "message": "Patient created."}

    except SQLAlchemyError as e:
        # Em caso de erro fazer rollback e retornar o erro
        db_session.rollback()

        error_message = str(e.__dict__.get("orig"))
        
        return {"status": "error", "message": "Error creating patient.", "details": error_message}

    finally:
        db_session.close()

# DELETE PATIENT BY ID
@app.delete("/delete_patient/{patient_id}")
async def delete_patient(patient_id: int):
    db_session = SessionLocal()
    
    try:
        result = db_session.execute(text("DELETE FROM Patient WHERE PatientID = :patient_id"), {"patient_id": patient_id})
        
        if result.rowcount == 0:
            return {"status": "error", "message": "Patient not found"}
        
        db_session.commit()
        return {"status": "success", "message": "Patient deleted."}
        
    except SQLAlchemyError as e:
        db_session.rollback()
        error_message = str(e.__dict__.get("orig"))
        return {"status": "error", "message": "Error deleting patient.", "details": error_message}
    
    finally:
        db_session.close()


# UPDATE PATIENT BY ID (VER SE SERIA MELHOR FAZER AUTOMATICO)
@app.put("/update_patient/{patient_id}")
async def update_patient(patient_id: int, item: Patient):
    db_session = SessionLocal()
    
    try:
        result = db_session.execute(
            text("""
                UPDATE Patient 
                SET Name = :Name, 
                    DateOfBirth = :DateOfBirth, 
                    GenderID = :GenderID, 
                    ContactNumber = :ContactNumber, 
                    Email = :Email, 
                    Address = :Address, 
                    HealthInsuranceID = :HealthInsuranceID 
                WHERE PatientID = :patient_id
            """),
            {
                "Name": item.Name,
                "DateOfBirth": item.DateOfBirth,
                "GenderID": item.GenderID,
                "ContactNumber": item.ContactNumber,
                "Email": item.Email,
                "Address": item.Address,
                "HealthInsuranceID": item.HealthInsuranceID,
                "patient_id": patient_id
            }
        )

        if result.rowcount == 0:
            return {"status": "error", "message": "Patient not found"}
        
        db_session.commit()
        return {"status": "success", "message": "Patient updated successfully ddd."}
        
    except SQLAlchemyError as e:
        db_session.rollback()
        error_message = str(e.__dict__.get("orig"))
        return {"status": "error", "message": "Error updating patient.", "details": error_message}
    
    finally:
        db_session.close()

# Start service
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)