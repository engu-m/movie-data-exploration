from dash import Dash, html, dash_table, dcc, callback, Output, Input
import pandas as pd
import numpy as np
import os
import plotly.express as px
import dash_bootstrap_components as dbc
from IPython.display import clear_output
import dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from collections import OrderedDict


from pymongo import MongoClient

dotenv.load_dotenv(override=True)

MONGO_DB_URI = os.getenv("MONGO_DB_URI")
ADAPTABLE_TRUST_PROXY_DEPTH = os.getenv("ADAPTABLE_TRUST_PROXY_DEPTH", "0")


clear_output()

client = MongoClient(MONGO_DB_URI, tls=True)
db = client.mycinema
coll = db.movies
reduced_coll = db.reduced_movies

app = Dash(__name__, external_stylesheets=[dbc.themes.CERULEAN])
server = app.server

# trust proxies behind which the deployed app is hiding
server.wsgi_app = ProxyFix(server.wsgi_app, x_for=1 + int(ADAPTABLE_TRUST_PROXY_DEPTH))

app.title = "Movie data explorer"  # Webpage title

dtable = dash_table.DataTable(
    sort_action="native",
    page_size=20,
    style_table={"overflowX": "auto"},
    style_cell={"font-family": "sans-serif"},
)

loading_table = dcc.Loading(type="default", children=dtable)

scatterplot = dcc.Graph()
loading_scatterplot = dcc.Loading(type="default", children=scatterplot)


default_values = OrderedDict(
    {
        "min_vote_count": 50,
        "min_vote_average": 0,
        "max_vote_average": 10,
        "min_runtime": 60,
        "max_runtime": 280,
    }
)

vote_count_slider = dcc.Slider(
    min=0,
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
    tooltip={"placement": "bottom"},
)

runtime_slider = dcc.RangeSlider(
    value=[default_values["min_runtime"], default_values["max_runtime"]],
    step=10,
    marks={int(i): f"{i:.0f}" for i in np.linspace(0, 500, 21)},
    tooltip={"placement": "bottom"},
)

reset_sliders_button = dbc.Button(children="Reset")


@callback(
    Output(vote_count_slider, "value"),
    Output(vote_average_slider, "value"),
    Output(runtime_slider, "value"),
    Input(reset_sliders_button, "n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(_):
    a, b, c, d, e = default_values.values()
    return a, [b, c], [d, e]


@callback(
    Output(scatterplot, component_property="figure"),
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
    query_result = collection.find(query, {"_id": 0, "genres": 0, "production_countries": 0})
    query_result_list = list(query_result)
    movie_data_sampled = pd.DataFrame(query_result_list)
    # add some jitter for scatterplot viz
    movie_data_sampled["vote_average_jitter"] = movie_data_sampled[
        "vote_average"
    ] + 0.02 * np.random.randn(len(movie_data_sampled))
    movie_data_sampled["runtime_jitter"] = movie_data_sampled["runtime"] + 0.3 * np.random.randn(
        len(movie_data_sampled)
    )

    fig = px.scatter(
        movie_data_sampled,
        x="runtime_jitter",
        y="vote_average_jitter",
        hover_name="movie_title",
        hover_data={
            "movie_title": True,
            "year_released": True,
            "runtime": True,
            "runtime_jitter": False,
            "vote_average": True,
            "vote_average_jitter": False,
        },
        size_max=12,
        height=600,
    )
    fig.update_layout(xaxis_title="Runtime (in minutes)", yaxis_title="Vote average")
    return fig, query_result_list


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
                reset_sliders_button,
            ],
            className="p-3 m-3 bg-light rounded-3",
        ),
        dbc.Row(loading_scatterplot),
        dbc.Row(loading_table),
        html.Br(),
        html.Hr(),
        html.Footer(children="Powered with Dash and Adaptable", style={"text-align": "right"}),
    ],
    fluid=True,
)

if __name__ == "__main__":
    app.run(debug=True)
