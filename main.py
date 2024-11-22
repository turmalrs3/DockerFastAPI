# API
from fastapi import FastAPI
import uvicorn
# Requests
import asyncio
import httpx
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


# GET PATIENT BY ID
@app.get("/patient/{patient_id}", tags=["Patients"])
async def get_patient(patient_id: int):
    db_session = SessionLocal()

    try:
        result = db_session.execute(text("SELECT * FROM Patient WHERE PatientID = :patient_id"), {"patient_id": patient_id})
        results = result.fetchone()
        
        async with httpx.AsyncClient() as client:
            # Request ao servico que tem o get gender by id
            gender_response = await client.get(f"http://3.88.215.11:8005/gender/{results['GenderID']}")

            user_gender = gender_response.json().get("data")
            results = dict(results)
            results["Gender"] = user_gender["Gender"]

        return {"status": "success", "data": results}

    except Exception as e:
        return {"status": "error", "message": f"Error retrieving patient: {str(e)}"}

@app.get("/patients", tags=["Patients"])
async def get_patients():
    db_session = SessionLocal()

    try:
        # Fetch all patients from the database
        result = db_session.execute(text("SELECT * FROM Patient"))
        results = result.fetchall()

        patients_list = [dict(row) for row in results]

        async with httpx.AsyncClient() as client:
            # Verificar todos o genero de todos os pacientes juntos
            tasks = [client.get(f"http://3.88.215.11:8005/gender/{patient['GenderID']}") for patient in patients_list]

            gender_responses = await asyncio.gather(*tasks)

        for i, gender_response in enumerate(gender_responses):
            if gender_response.status_code == 200:
                user_gender = gender_response.json().get("data")
                patients_list[i]["Gender"] = user_gender["Gender"]
            else:
                patients_list[i]["Gender"] = None  # Caso a API falhe

        return {"status": "success", "data": patients_list}

    except Exception as e:
        return {"status": "error", "message": f"Error retrieving patients: {str(e)}"}
    
# CREATE PATIENT
@app.post("/create_patient", tags=["Patients"])
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
@app.delete("/delete_patient/{patient_id}", tags=["Patients"])
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
@app.put("/update_patient/{patient_id}", tags=["Patients"])
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
        return {"status": "success", "message": "Patient updated successfully."}
        
    except SQLAlchemyError as e:
        db_session.rollback()
        error_message = str(e.__dict__.get("orig"))
        return {"status": "error", "message": "Error updating patient.", "details": error_message}
    
    finally:
        db_session.close()



# APPOINTMENTS

# CREATE APPOINTMENT
@app.post("/create_appointment", tags=["Appointments"])
async def create_appointment(item: Appointment):
    db_session = SessionLocal()

    try:
        db_session.execute(
            text(""" INSERT INTO Appointment (PatientID, DoctorID, DoctorClinicID, AppointmentDateTime, AppointmentStatusID, ReasonForVisit, DoctorNotes, CheckInStatus, TreatmentID)
                VALUES (:PatientID, :DoctorID, :DoctorClinicID, :AppointmentDateTime, :AppointmentStatusID, :ReasonForVisit, :DoctorNotes, :CheckInStatus, :TreatmentID )"""),
            {
                "PatientID": item.PatientID,
                "DoctorID": item.DoctorID,
                "DoctorClinicID": item.DoctorClinicID,
                "AppointmentDateTime": item.AppointmentDateTime,
                "AppointmentStatusID": item.AppointmentStatusID,
                "ReasonForVisit": item.ReasonForVisit,
                "DoctorNotes": item.DoctorNotes,
                "CheckInStatus": item.CheckInStatus,
                "TreatmentID": item.TreatmentID
            }
        )
        db_session.commit()

        return {"status": "success", "message": "Appointment created."}

    except SQLAlchemyError as e:
        db_session.rollback()

        error_message = str(e.__dict__.get("orig"))
        
        return {"status": "error", "message": "Error creating appointment.", "details": error_message}

    finally:
        db_session.close()

# GET APPOINTMENT BY ID
@app.get("/appointment/{appointment_id}", tags=["Appointments"])
async def get_appointment(appointment_id: int):
    db_session = SessionLocal()

    try:
        result = db_session.execute(text("SELECT * FROM Appointment WHERE AppointmentID = :appointment_id"), {"appointment_id": appointment_id})
        results = result.fetchone()

        return {"status": "success", "data": dict(results)}

    except Exception as e:
        return {"status": "error", "message": f"Error retrieving appointment: {str(e)}"}

# GET ALL APPOINTMENTS
@app.get("/appointments", tags=["Appointments"])
async def get_appointments():
    db_session = SessionLocal()

    try:
        result = db_session.execute(text("SELECT * FROM Appointment"))
        results = result.fetchall()

        appointments_list = [dict(row) for row in results]

        return {"status": "success", "data": appointments_list}

    except Exception as e:
        return {"status": "error", "message": f"Error retrieving appointments: {str(e)}"}

# DELETE APPOINTMENT BY ID
@app.delete("/delete_appointment/{appointment_id}", tags=["Appointments"])
async def delete_appointment(appointment_id: int):
    db_session = SessionLocal()
    
    try:
        result = db_session.execute(text("DELETE FROM Appointment WHERE AppointmentID = :appointment_id"), {"appointment_id": appointment_id})
        
        if result.rowcount == 0:
            return {"status": "error", "message": "Appointment not found"}
        
        db_session.commit()
        return {"status": "success", "message": "Appointment deleted."}
        
    except SQLAlchemyError as e:
        db_session.rollback()
        error_message = str(e.__dict__.get("orig"))
        return {"status": "error", "message": "Error deleting appointment.", "details": error_message}
    
    finally:
        db_session.close()

# UPDATE APPOINTMENT BY ID
@app.put("/update_appointment/{appointment_id}", tags=["Appointments"])
async def update_appointment(appointment_id: int, item: Appointment):
    db_session = SessionLocal()
    
    try:
        result = db_session.execute(
            text("""
                UPDATE Appointment
                SET PatientID = :PatientID, 
                    DoctorID = :DoctorID, 
                    DoctorClinicID = :DoctorClinicID, 
                    AppointmentDateTime = :AppointmentDateTime, 
                    AppointmentStatusID = :AppointmentStatusID, 
                    ReasonForVisit = :ReasonForVisit, 
                    DoctorNotes = :DoctorNotes, 
                    CheckInStatus = :CheckInStatus, 
                    TreatmentID = :TreatmentID 
                WHERE AppointmentID = :appointment_id
            """),
            {
                "PatientID": item.PatientID,
                "DoctorID": item.DoctorID,
                "DoctorClinicID": item.DoctorClinicID,
                "AppointmentDateTime": item.AppointmentDateTime,
                "AppointmentStatusID": item.AppointmentStatusID,
                "ReasonForVisit": item.ReasonForVisit,
                "DoctorNotes": item.DoctorNotes,
                "CheckInStatus": item.CheckInStatus,
                "TreatmentID": item.TreatmentID,
                "appointment_id": appointment_id
            }
        )

        if result.rowcount == 0:
            return {"status": "error", "message": "Appointment not found"}
        
        db_session.commit()
        return {"status": "success", "message": "Appointment updated successfully."}
        
    except SQLAlchemyError as e:
        db_session.rollback()
        error_message = str(e.__dict__.get("orig"))
        return {"status": "error", "message": "Error updating appointment.", "details": error_message}
    
    finally:
        db_session.close()

# Start service
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
