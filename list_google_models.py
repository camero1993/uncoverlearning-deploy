import google.generativeai as genai
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def list_generative_models():
    """Lists available generative models from Google AI."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("Error: GEMINI_API_KEY environment variable not set.")
        logger.error("Please set it before running this script.")
        return

    try:
        genai.configure(api_key=api_key)
        logger.info("Successfully configured Google Generative AI API.")
    except Exception as e:
        logger.error(f"Error configuring Google Generative AI API: {e}")
        return

    logger.info("Available models from Google Generative AI (supporting 'generateContent'):")
    try:
        models_found = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models_found = True
                logger.info(f"  Model Name: {m.name}")
                logger.info(f"    Display Name: {m.display_name}")
                # logger.info(f"    Description: {m.description}") # Can be verbose
                logger.info(f"    Supported Generation Methods: {m.supported_generation_methods}")
                logger.info("-" * 20)
        if not models_found:
            logger.info("No models found that support 'generateContent'.")
            logger.info("This might indicate an issue with API key permissions or that no suitable models are available.")
            logger.info("You can also check the full list of models and their capabilities at https://ai.google.dev/models")

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        logger.error("This could be due to an invalid API key, network issues, or incorrect permissions.")

if __name__ == "__main__":
    list_generative_models() 