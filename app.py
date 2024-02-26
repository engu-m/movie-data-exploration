from dash import Dash, html, dash_table, dcc, callback, Output, Input
import pandas as pd
import numpy as np
import os
import plotly.express as px
import dash_bootstrap_components as dbc
from IPython.display import clear_output
import dotenv

from pymongo import MongoClient

dotenv.load_dotenv(override=True)

MONGO_DB_URI = os.getenv("MONGO_DB_URI")


clear_output()

client = MongoClient(MONGO_DB_URI)
db = client.mycinema
coll = db.movies
reduced_coll = db.reduced_movies

app = Dash(__name__, external_stylesheets=[dbc.themes.CERULEAN])

server = app.server

dtable = dash_table.DataTable(
    sort_action="native",
    page_size=10,
    style_table={"overflowX": "auto"},
    style_cell={"font-family": "sans-serif"},
)

loading_table = dcc.Loading(type="default", children=dtable)

histogram = dcc.Graph()
loading_histogram = dcc.Loading(type="default", children=histogram)


default_values = {
    "min_vote_count": 50,
    "min_vote_average": 0,
    "max_vote_average": 10,
    "min_runtime": 60,
    "max_runtime": 280,
}

vote_count_slider = dcc.Slider(
    min=1,
    max=1000,
    step=5,
    value=default_values["min_vote_count"],
    marks={1: "1", 1000: "1000"},
    tooltip={"placement": "bottom", "always_visible": True},
)

vote_average_slider = dcc.RangeSlider(
    min=0,
    max=10,
    step=0.1,
    value=[default_values["min_vote_average"], default_values["max_vote_average"]],
    marks={i: str(i) for i in range(11)},
    # dots=True,
    tooltip={"placement": "bottom"},
)

runtime_slider = dcc.RangeSlider(
    value=[default_values["min_runtime"], default_values["max_runtime"]],
    step=10,
    marks={int(i): f"{i:.0f}" for i in np.linspace(0, 500, 21)},
    tooltip={"placement": "bottom"},
)


@callback(
    Output(histogram, component_property="figure"),
    Output(dtable, component_property="data"),
    Input(vote_count_slider, "value"),
    Input(vote_average_slider, "value"),
    Input(runtime_slider, "value"),
)
def update_table_and_graph(min_vote_count, vote_averages, runtimes):
    min_vote_average, max_vote_average = vote_averages
    min_runtime, max_runtime = runtimes

    if (
        (min_runtime >= default_values["min_runtime"])
        and (max_runtime <= default_values["max_runtime"])
        and (min_vote_count >= default_values["min_vote_count"])
        and (min_vote_average >= default_values["min_vote_average"])
        and (max_vote_average <= default_values["max_vote_average"])
    ):
        # use stored view to reduce computation costs
        collection = reduced_coll
    else:
        # use full database instead. Slower
        collection = coll

    query = {
        "runtime": {"$gte": min_runtime, "$lte": max_runtime},
        "vote_count": {"$gte": min_vote_count},
        "vote_average": {"$gte": min_vote_average, "$lte": max_vote_average},
    }
    query_result = collection.find(query)
    movie_data_sampled = pd.DataFrame(list(query_result))
    movie_data_sampled.drop("_id", axis=1, inplace=True)
    movie_data_sampled = movie_data_sampled.astype({"genres": str, "production_countries": str})

    fig = px.scatter(
        movie_data_sampled,
        x="runtime",
        y="vote_average",
        hover_name="movie_title",
        hover_data={
            # "image_url" : True,
            # "movie_id" : True,
            "movie_title": True,
            "year_released": True,
            # "popularity" : True,
            "runtime": True,
            "vote_average": True,
            "vote_count": True,
            "genres": True,
            # "production_countries" : True,
            # "spoken_languages" : True,
            # "tmdb_id" : True,
        },
        size_max=10,
    )
    return fig, movie_data_sampled.to_dict("records")


app.layout = dbc.Container(
    [
        dbc.Row(
            [
                html.Div(
                    children="Exploring movie dataset", className="text-primary text-center fs-3"
                )
            ]
        ),
        dbc.Row([html.Hr()]),
        html.Div(
            [
                dbc.Row(
                    [
                        html.Div(children="Minimum vote count", className="text-center"),
                        vote_count_slider,
                        html.Br(),
                    ]
                ),
                dbc.Row(
                    [
                        html.Div(children="Vote average", className="text-center"),
                        vote_average_slider,
                        html.Br(),
                    ]
                ),
                dbc.Row(
                    [
                        html.Div(children="Runtime (minutes)", className="text-center"),
                        runtime_slider,
                        html.Br(),
                    ]
                ),
            ],
            className="p-3 m-3 bg-light rounded-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [loading_table],
                    width=6,
                ),
                dbc.Col(
                    [loading_histogram],
                    width=6,
                ),
            ],
        ),
    ],
    fluid=True,
)

if __name__ == "__main__":
    app.run(debug=True)
