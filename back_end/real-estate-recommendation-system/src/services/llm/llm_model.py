from typing import Tuple, Optional
import random
import io
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from loguru import logger
import random

from src.settings.config import APPLICATION
from src.services.llm.const.list_models import GEMINI_MODELS

API_KEYS = APPLICATION.get("gemini_api_keys", "")


class LLModel:
    """A class to handle interactions with Google's Gemini AI model.

    This class provides methods to interact with Google's Gemini AI models,
    handling configuration, safety settings, and error retries.
    """

    def __init__(
            self,
            model_name: str = GEMINI_MODELS["GEMINI_2_5_FLASH"],
            temperature: float = 0.5,
            top_p: float = 1.0,
            top_k: int = 30,
            max_output_tokens: int = 1024 * 20
    ) -> None:
        """Initialize the GeminiModel with configuration parameters.

        Args:
            model_name: The name of the Gemini model to use.
            temperature: Controls randomness in the response (0.0 to 1.0).
            top_p: Controls diversity via nucleus sampling (0.0 to 1.0).
            top_k: Controls diversity via top-k sampling (1 to 40).
            max_output_tokens: Maximum number of tokens in the response.
        """
        self.model_name = model_name
        self.generation_config = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_output_tokens": max_output_tokens,
        }
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    
    def start(self):
        try:
            self.api_keys = [key.strip() for key in API_KEYS.split(",") if key.strip()]
        except Exception as e:
            logger.error(f"Error starting GeminiModel: {str(e)}")
            raise
    
    async def ask_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = GEMINI_MODELS["GEMINI_2_5_FLASH"],
        retries: int = 3,
        timeout_seconds: int = 60 * 10
    ) -> Tuple[bool, Optional[str], Optional[Exception]]:
        return await self._ask_gemini(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            retries=retries,
            timeout_seconds=timeout_seconds
        )

    async def _ask_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = GEMINI_MODELS["GEMINI_2_5_FLASH"],
        retries: int = 3,
        timeout_seconds: int = 60 * 10
    ) -> Tuple[bool, Optional[str], Optional[Exception]]:
        """Ask a question to the Gemini model and get a response.

        Args:
            system_prompt: The system prompt to set the context.
            user_prompt: The user's question or prompt.
            model_llm: The specific Gemini model to use.
            retries: Number of retry attempts if the request fails.
            timeout_seconds: Timeout for the request in seconds.

        Returns:
            A tuple containing:
            - success status (bool)
            - response text (str) or None if failed
            - exception (Exception) or None if successful
        """
        try:
            api_key = random.choice(self.api_keys)
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel(
                model_name=model,
                generation_config=self.generation_config,
                system_instruction=system_prompt,
                safety_settings=self.safety_settings,
            )

            try:
                message = [{'role': 'user', 'parts': [user_prompt]}]
                response = await model.generate_content_async(
                    message,
                    request_options={'timeout': timeout_seconds}
                )
                return True, response.parts[0].text, None

            except Exception as e:
                logger.error(f"Error generating content with Gemini: {str(e)}")
                raise

        except Exception as e:
            retries -= 1
            if retries > 0:
                logger.warning(
                    f"Retrying Gemini request ({4 - retries}/3). Error: {e}")
                return await self._ask_gemini(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model,
                    retries=retries,
                    timeout_seconds=timeout_seconds
                )
            else:
                logger.error(
                    f"Failed to get response from Gemini after all retries: {e}")
                return False, None, e