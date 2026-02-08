from pydantic import BaseModel, Field, field_validator
import re

class Structure(BaseModel):
    tldr: str = Field(description="generate a too long; didn't read summary")
    tldr_vn: str = Field(description="Vietnamese translation of tldr")
    motivation: str = Field(description="describe the motivation in this paper")
    motivation_vn: str = Field(description="Vietnamese translation of motivation")
    method: str = Field(description="method of this paper")
    method_vn: str = Field(description="Vietnamese translation of method")
    result: str = Field(description="result of this paper")
    result_vn: str = Field(description="Vietnamese translation of result")
    conclusion: str = Field(description="conclusion of this paper")
    conclusion_vn: str = Field(description="Vietnamese translation of conclusion")