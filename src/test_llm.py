from inquira.llm_service import LLMService
from pydantic import BaseModel

class ResponseType(BaseModel):
    output: str

if __name__ == '__main__':
    llm = LLMService(api_key="AIzaSyAMMWwaKUUHJJVWeSIrtd4-z4Uj6L_fKYs")

    response = llm.ask(
        user_query="tell me a joke",
        structured_output_format=ResponseType
    )

    print(response)