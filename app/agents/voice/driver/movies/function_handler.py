import json
from loguru import logger
from pipecat.services.llm_service import FunctionCallParams

async def search_movies_handler(params: FunctionCallParams):
    """Handler for search_movies tool - returns mock movie search results"""
    logger.info(f"search_movies_handler called with parameters: {params.arguments}")
    
    # Extract parameters
    query = params.arguments.get("query", "")
    year = params.arguments.get("year", "")
    genre = params.arguments.get("genre", "")
    
    # Mock search results based on query
    result = {
        "success": True,
        "search_query": query,
        "filters": {
            "year": year if year else "Any",
            "genre": genre if genre else "Any"
        },
        "total_results": 3,
        "movies": [
            {
                "title": "The Stellar Journey",
                "year": 2023,
                "genre": "Sci-Fi Adventure",
                "rating": 8.5,
                "description": "An epic space odyssey about humanity's first mission beyond our solar system.",
                "duration": "148 min"
            },
            {
                "title": "Midnight Echo",
                "year": 2024,
                "genre": "Thriller",
                "rating": 8.2,
                "description": "A psychological thriller that keeps you guessing until the very end.",
                "duration": "125 min"
            },
            {
                "title": "Hearts in Spring",
                "year": 2023,
                "genre": "Romance Comedy",
                "rating": 7.8,
                "description": "A heartwarming romantic comedy about finding love in unexpected places.",
                "duration": "112 min"
            }
        ],
        "recommendation": f"Found {3} great movies matching '{query}'. Would you like details about any of these?"
    }
    
    await params.result_callback(result)

async def get_movie_details_handler(params: FunctionCallParams):
    """Handler for get_movie_details tool - returns mock detailed movie information"""
    logger.info(f"get_movie_details_handler called with parameters: {params.arguments}")
    
    # Extract parameters
    movie_title = params.arguments.get("movie_title", "Unknown Movie")
    include_spoilers = params.arguments.get("include_spoilers", False)
    
    # Mock detailed movie information
    result = {
        "success": True,
        "movie": {
            "title": movie_title,
            "year": 2023,
            "genre": ["Sci-Fi", "Adventure", "Drama"],
            "rating": 8.5,
            "imdb_rating": "8.5/10",
            "duration": "148 min",
            "director": "Sarah Martinez",
            "writers": ["John Anderson", "Emily Chen"],
            "cast": [
                {"name": "Chris Evans", "role": "Captain Alex Turner"},
                {"name": "Zendaya", "role": "Dr. Maya Patel"},
                {"name": "Idris Elba", "role": "Commander James Foster"},
                {"name": "Florence Pugh", "role": "Engineer Lisa Wong"}
            ],
            "plot": "In the year 2045, humanity embarks on its most ambitious mission yet - sending a crew beyond our solar system to explore a newly discovered habitable planet. As the crew faces unprecedented challenges in deep space, they must confront not only the mysteries of the universe but also the limits of human endurance and the bonds that hold them together." + (
                " The journey takes a dramatic turn when they discover signs of intelligent life on the destination planet." if include_spoilers else ""
            ),
            "awards": [
                "Academy Award - Best Visual Effects",
                "Golden Globe - Best Original Score",
                "BAFTA - Best Cinematography"
            ],
            "user_reviews": {
                "average_rating": 4.3,
                "total_reviews": 15847,
                "positive": "A breathtaking space epic with stunning visuals and emotional depth.",
                "critical": "Pacing could be tighter in the second act."
            },
            "similar_movies": [
                "Interstellar (2014)",
                "The Martian (2015)",
                "Arrival (2016)"
            ],
            "available_on": ["Netflix", "Amazon Prime", "Apple TV+"]
        },
        "recommendation": f"'{movie_title}' is highly rated with an 8.5/10 score. Would you like similar movie recommendations?"
    }
    
    await params.result_callback(result)

