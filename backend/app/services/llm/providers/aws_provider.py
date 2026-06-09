import os
from .base import BaseProvider
from langchain_core.language_models.chat_models import BaseChatModel
from app.config import settings

class AWSProvider(BaseProvider):
    @classmethod
    def get_name(cls) -> str:
        return "aws"
        
    @classmethod
    def create_llm(cls, **kwargs) -> BaseChatModel:
        try:
            from langchain_aws import ChatBedrock
        except ImportError:
            raise ImportError("Please install langchain-aws to use the AWS Bedrock provider.")
            
        model_id = kwargs.get("model_name", settings.AWS_BEDROCK_MODEL)
        temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
        region = os.getenv("AWS_REGION", "us-east-1")
        
        # Note: langchain_aws uses the standard boto3 environment variables implicitly
        # (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
        return ChatBedrock(
            model_id=model_id,
            region_name=region,
            model_kwargs={"temperature": temperature}
        )
