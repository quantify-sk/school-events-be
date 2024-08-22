from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Report(Base):
    __tablename__ = "report"
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(255), nullable=False)
    generated_on = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(Integer, ForeignKey("user.user_id"))

    def __init__(self, report_type: str, generated_by: int):
        self.report_type = report_type
        self.generated_by = generated_by

    def _to_model(self):
        return {
            "id": self.id,
            "report_type": self.report_type,
            "generated_on": self.generated_on,
            "generated_by": self.generated_by,
        }

    @classmethod
    def generate_report(cls):
        pass

    @classmethod
    def export_report(cls, format):
        pass
