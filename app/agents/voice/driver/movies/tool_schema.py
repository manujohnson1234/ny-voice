from pipecat.adapters.schemas.function_schema import FunctionSchema

search_movies = FunctionSchema(
    name="search_movies",
    description="Search for movies based on genre, year, keyword, or mood. Returns a list of matching movies with basic information.",
    properties={
        "query": {
            "type": "string",
            "description": "Search query - can be genre, keyword, actor name, or movie theme"
        },
        "year": {
            "type": "string",
            "description": "Optional: Filter by release year or year range (e.g., '2023' or '2020-2023')"
        },
        "genre": {
            "type": "string",
            "description": "Optional: Specific genre filter (action, comedy, drama, thriller, sci-fi, romance, horror, etc.)"
        }
    },
    required=["query"]
)

get_movie_details = FunctionSchema(
    name="get_movie_details",
    description="Get comprehensive details about a specific movie including full plot, cast, crew, ratings, reviews, and similar movie recommendations.",
    properties={
        "movie_title": {
            "type": "string",
            "description": "The title of the movie to get details for"
        },
        "include_spoilers": {
            "type": "boolean",
            "description": "Whether to include spoiler information in the plot summary. Default is false."
        }
    },
    required=["movie_title"]
)

