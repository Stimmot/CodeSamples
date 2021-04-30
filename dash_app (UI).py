import base64
import json
import locale
import random
from datetime import datetime as dt

import pandas as pd

from elasticsearch import Elasticsearch
import requests

import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import dash_daq as daq

# set time format
locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')

""" --- Test connection --- """

r = requests.get('http://localhost:9200')
print(r.content)


""" -- Elastic -- """

# Connect to the elastic cluster
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])


# load initial data from Elasticsearch
def load_data():
    res = es.search(index='urteile',
                    body={
                        "size": 400,
                        'query': {
                            "match_all": {}
                        }
                    })

    results = res['hits']['hits']

    # keys as a list
    data_keys = ['date', 'gericht', 'delikt', 'vorstrafe', 'gestaendnis', 'schaden', 'strafmass_betrag',
                 'strafmass_tagessatz',
                 'id', 'body']

    # iterate through results and keys, add values to a tuple if keys match
    tuple_list = []
    for result in results:
        source_tuple = ()
        source = result["_source"]
        for key in data_keys:
            for item in source:
                if key == item:
                    if item == "date":
                        source_tuple = source_tuple + (dt.fromtimestamp(source[item] / 1000.0),)
                    elif item == "gestaendnis" or item == "vorstrafe":
                        if source[item] is True:
                            source_tuple = source_tuple + ("Ja",)
                        else:
                            source_tuple = source_tuple + ("Nein",)
                    elif item == "body":
                        # append id
                        source_tuple = source_tuple + (result["_id"],)
                        source_tuple = source_tuple + (source[item],)
                    else:
                        source_tuple = source_tuple + (source[item],)

        # then add tuple to a list
        tuple_list.append(source_tuple)

    # build a dataframe out of tuple list
    data_frame = pd.DataFrame(tuple_list, columns=data_keys, index=[i for i in range(len(results))])
    # FIXME: noise for demonstrator
    #data_frame["schaden"] = [x + random.randrange(-12, 12) if x == 50 else x for x in data_frame["schaden"]]

    # testing: print dataframe
    with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.expand_frame_repr', False):
        # print(data_frame)
        pass

    return data_frame


""" -- CSS -- """

# use external css
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', dbc.themes.BOOTSTRAP]

tabs_styles = {
    'height': '44px',
    'margin-top': '30px'
}
tab_style = {
    'borderBottom': '1px solid #d6d6d6',
    'padding': '15px',
}
tab_selected_style = {
    'borderTop': '1px solid #d6d6d6',
    'borderBottom': '1px solid #d6d6d6',
    'backgroundColor': '#119DFF',
    'color': 'white',
    'padding': '15px'
}

""" -- Dash -- """


# function to generate table out of dataframe
def generate_table(dataframe, max_rows=15):
    return html.Table([
        html.Thead(
            html.Tr([html.Th(col) for col in dataframe.columns])
        ),
        html.Tbody([
            html.Tr([
                html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
            ]) for i in range(min(len(dataframe), max_rows))
        ])
    ])


""" -- Initialize -- """
# Call to load data
urteile_df = load_data()
gerichte_namen = urteile_df['gericht'].unique()

image_1 = "Bilder/logo_1.png"
encoded_image_1 = base64.b64encode(open(image_1, 'rb').read())
image_2 = "Bilder/logo_2.png"
encoded_image_2 = base64.b64encode(open(image_2, 'rb').read())

# -!- Start App -!- #
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

""" -- Layout -- """

# Plot Hover
app.layout = html.Div(children=[

    # --- Top --- #
    html.Div(id="menu", children=[

        # -- Titel --
        dbc.Row(children=[
            dbc.Col(html.Div(html.H2("Suche"), style={"padding": "10px"})),
        ]),

        # -- Filter --
        dbc.Row([

            # - Puffer -
            dbc.Col(width=1, sm=1),

            # - Input/Gericht/Datum -
            dbc.Col([

                # Überschrift
                html.Div([
                    dbc.Row(dbc.Col(html.H3("Metadaten")))
                ]),

                # ID Input
                html.Div([
                    dbc.Row(dbc.Col(html.H4("Volltext-ID"))),
                    dbc.Row(dbc.Col(
                        dcc.Input(
                            id='volltext_id',
                            placeholder='ID eingeben...',
                            type='text',
                            value=''
                        ), width=1)
                    ),
                ]),

                # Gericht Dropdown
                html.Div([
                    dbc.Row(dbc.Col(html.H4("Gericht"))),
                    dbc.Row(dbc.Col(
                        dcc.Dropdown(
                            id='gericht',
                            placeholder='Auswählen...',
                            options=[{'label': i, 'value': i} for i in sorted(gerichte_namen)],
                            multi=True,
                            style={"font-size": "12px"}
                        ), width=8)
                    ),
                ], style={"margin-top": "10px"}),

                # Date
                html.Div([
                    dbc.Row(dbc.Col(html.H4(children="Datum"))),
                    dbc.Row(dbc.Col(dcc.DatePickerRange(
                        id='my-date-picker-range',
                        min_date_allowed=dt(1900, 1, 1),
                        max_date_allowed=dt(2025, 1, 1),
                        display_format='DD.MM.YYYY',
                        start_date_placeholder_text='TT.MM.JJJJ',
                        initial_visible_month=dt(2017, 8, 5),
                        start_date=dt(1950, 1, 1).date(),
                        end_date=dt(2020, 1, 1).date()
                    ))),
                ], style={"margin-top": "10px"}),

            ],
                width={"size": 3},
                style={"padding-top": "10px", "padding-bottom": "10px", "border-style": "solid",
                       "border-width": "thin", "background-color": "#F5F5F5", "margin-left":"-65px"}),

            # - Vorstr/Gest/Schaden/Delikt/Button -
            dbc.Col([

                # Überschrift
                html.Div([
                    dbc.Row(dbc.Col(html.H3("Inhaltliche Daten")))
                ]),

                # Schadenshöhe
                dbc.Row(
                    dbc.Col(
                        html.Div([
                            html.H4(children="Schadenshöhe"),

                            # Auswahl
                            html.Div([
                                dcc.Input(id="slider_min", type="number", value=0, size="7"),

                                html.Div(" bis ",
                                         style={"display": "inline-block", "margin-left": "15px",
                                                "margin-right": "15px", "font-size": "14px"}),

                                dcc.Input(id="slider_max", type="number", value=500, size="7"),

                            ], style={"display": "inline-block"}),

                        ]),
                    ),
                ),

                # Delikt Dropdown
                html.Div([
                    dbc.Row(dbc.Col(html.H4("Delikt"))),
                    dbc.Row(dbc.Col(
                        dcc.Dropdown(
                            id='delikt',
                            placeholder='Auswählen...',
                            options=[{'label': 'Diebstahl', 'value': 'Diebstahl'}],
                            multi=True,
                            style={"font-size": "12px"}
                        ), width=6),
                    ),
                ], style={"margin-top": "10px"}),

                # Vorstrafen & Geständnis
                dbc.Row([

                    # Vorstrafen
                    dbc.Col([
                        daq.ToggleSwitch(
                            id="vorstr_checkbox",
                            style={"font-size": "15px"},
                            label="Vorstrafen",
                            size=40,
                            color="rgb(17, 157, 255)",
                        ),
                        html.Div([
                            dcc.RadioItems(
                                id='vorstr',
                                options=[{'label': i, 'value': i} for i in ['Ja', 'Nein']],
                                value='Ja',
                                labelStyle={'display': 'inline-block'},
                            ),
                        ], style={'margin-left': "25px", "margin-top": "10px", 'display': 'block', "font-size": "14px"}),
                    ], md=3),

                    # Geständnis
                    dbc.Col([
                        daq.ToggleSwitch(
                            id="gest_checkbox",
                            style={"font-size": "15px"},
                            label="Geständnis",
                            size=40,
                            color="rgb(17, 157, 255)",
                        ),
                        html.Div([
                            dcc.RadioItems(
                                id='gest',
                                options=[{'label': i, 'value': i} for i in ['Ja', 'Nein']],
                                value='Ja',
                                labelStyle={'display': 'inline-block'},
                            ),
                        ], style={'margin-left': "25px", "margin-top": "10px", 'display': 'block',
                                  "font-size": "14px"}),
                    ], md=3),
                ], style={"padding-top": "10px"}),

            ],
                width={"size": 3},
                style={"margin-left": "15px", "padding-top": "10px", "padding-bottom": "10px", "border-style": "solid",
                       "border-width": "thin", "background-color": "#F5F5F5"}),

            # - Button -
            dbc.Col([

                # Suchen
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Suchen", id="suchen", color="primary",
                                   style={"margin-top": "15px", "margin-left": "10px", "font-size": "13px"}),
                    ], width=3),


                # Reset
                    dbc.Col([
                        dbc.Button("Löschen", id="reset", color="link",
                                   style={"margin-top": "15px", "margin-left": "-25px", "font-size": "13px"}),
                    ], width=3),
                ]),

            ], width=3, className="mt-auto"),

            dbc.Col([

                html.Img(src='data:image/png;base64,{}'.format(encoded_image_1.decode()), width="200px", style={"padding-bottom": "45px"}),
                html.Img(src='data:image/png;base64,{}'.format(encoded_image_2.decode()), width="200px", style={"margin-left": "20px"}),

            ])

        ], justify="start", style={"padding-bottom": "10px"}),

    ], style={"padding": "10px", 'background-color': '#E8E8E8'}),

    # --- Bottom --- #
    html.Div([

        # --- Bottom Right Side --- #

        # -- Tabs --
        dbc.Row(
            dbc.Col([
                dbc.Row([
                    dcc.Tabs(id='tabs-example', value='tab-1', children=[
                        dcc.Tab(label='Tabelle', value='tab-1', style=tab_style,
                                selected_style=tab_selected_style),
                        dcc.Tab(label='Textsuche', value='tab-2', style=tab_style,
                                selected_style=tab_selected_style),
                    ], style=tabs_styles),
                ], justify="end"),
            ], width=10),
        ),

        # -- Tab Content --
        dbc.Row([
            dbc.Col([
                html.Div(children=[

                    # Graph & Tabelle
                    html.Div([
                        dbc.Row([

                            html.H2("Visualisierung"),
                            html.Br(),

                            # Toggle
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        daq.ToggleSwitch(id="map_toggle",
                                                         label="Karte",
                                                         labelPosition='bottom',
                                                         size=40,
                                                         color="rgb(17, 157, 255)",
                                                         value=False),
                                    ], style={"margin-left": "30px"}),
                                ]),
                            ]),

                            # Graph
                            dbc.Col(dcc.Graph(id='basic-interactions'), width=12),

                            # Map
                            html.Div([
                                html.Iframe(id="Switchin", src=(
                                    "http://localhost:5601/goto/ade7551b74d81297651fadaad70d4e1b?embed=true"),
                                            height="600", width="850"),
                            ]),

                            # Hover & Click Daten
                            dbc.Col([
                                html.Div(className='row', children=[
                                    html.Div([
                                        dcc.Markdown("Auswahl"),
                                        html.Pre(id='hover-data',
                                                 style={"padding": "15px",
                                                        "font-size": "14px",
                                                        "color": "#303030",
                                                        "border-style": "solid",
                                                        "border-width": "thin"
                                                        }),
                                    ], className='six columns'),

                                    html.Div([
                                        dcc.Markdown("Klick"),
                                        html.Pre(id='click-data',
                                                 style={"padding": "15px",
                                                        "font-size": "14px",
                                                        "color": "#303030",
                                                        "border-style": "solid",
                                                        "border-width": "thin"
                                                        }),
                                    ], className='six columns'),

                                ]),
                            ], width=10,
                                style={"padding": "20px",
                                       "margin-left": "45px",
                                       "margin-top": "15px",
                                       "font-size": "14px"}),

                        ]),
                        html.Br(),
                    ], style={"display": "block", "padding-left": "20px", "margin-left": "15px",
                              "margin-right": "10px"}),
                ]),
            ], width=6),

            # -- Tabelle --
            dbc.Col([
                html.Div(id="first_tab", children=[

                    html.H2("Tabelle"),
                    html.Br(),

                    # Average Table
                    dbc.Row([
                        dbc.Col(
                            html.Div(id="average", style={"height": "400"}),
                            style={"font-size": "12px", "float": "right", "margin-bottom": "10px"},
                            width=5
                        ),
                    ], justify="start"),

                    # Full Table
                    dbc.Row([
                        dbc.Col(
                            html.Div(children=[dash_table.DataTable(id="dash_table")], id="table_div",
                                     style={"height": "400"}),
                            style={"font-size": "12px"}
                        )
                    ]),
                ], style={"display": "block", "padding-top": "15px"}),

                # -- Text Search --
                html.Div(id="second_tab", children=[
                    html.Div([

                        html.Div([
                            # - Input -
                            dbc.Row([
                                html.H2('Volltextsuche'),
                            ]),
                            dbc.Row([
                                html.P(
                                    "Nach Eingabe einer Volltext-ID kann der Urteilstext eingesehen werden.",
                                    style={"font-size": "14px"}),
                            ]),
                            dbc.Row([
                                dcc.Input(id="id_input", value="Ag1uA3IBnBneUu2PqU8Q", type="text",
                                          placeholder="Og1tA3IB...", debounce=True),
                            ]),
                        ], style={'padding': '25px', "padding-left": "30px", 'background-color': '#E8E8E8'}),
                        # - Output -
                        html.Div(children=[], id="id_output", style={"margin-top": "15px"}),

                    ], style={"padding-top": "15px"})
                ], style={"display": "block"}),
            ], width=6),
        ], style={"margin-right": "15px"}),
    ]),
])

""" -- Plot Callbacks -- """


# Plot Hover
@app.callback(
    Output('hover-data', 'children'),
    [Input('basic-interactions', 'hoverData')])
def display_hover_data(hoverData):
    text = hoverData['points'][0]['text']
    text_id = text.split()[2]
    df_urteil = urteile_df[(urteile_df.id == text_id)]
    df_urteil = df_urteil.iloc[0]
    urteil_auszug = f"{df_urteil['gericht']}, {df_urteil['date']}" \
                    f"\n{df_urteil['delikt']}" \
                    f"\n{df_urteil['schaden']} Euro Schaden" \
                    f"\n{df_urteil['strafmass_tagessatz']} Tagessätze zu je {df_urteil['strafmass_betrag']} Euro" \
                    f"\nVorstrafen: {df_urteil['vorstrafe']} \nGeständnis: {df_urteil['gestaendnis']}" \
                    f"\n\n{df_urteil['id']}"
    return urteil_auszug


# Plot Click
@app.callback(
    Output('click-data', 'children'),
    [Input('basic-interactions', 'clickData')])
def display_click_data(clickData):
    text = clickData['points'][0]['text']
    text_id = text.split()[2]
    df_urteil = urteile_df[(urteile_df.id == text_id)]
    df_urteil = df_urteil.iloc[0]
    urteil_auszug = f"{df_urteil['gericht']}, {df_urteil['date']}" \
                    f"\n{df_urteil['delikt']}" \
                    f"\n{df_urteil['schaden']} Euro Schaden" \
                    f"\n{df_urteil['strafmass_tagessatz']} Tagessätze zu je {df_urteil['strafmass_betrag']} Euro" \
                    f"\nVorstrafen: {df_urteil['vorstrafe']} \nGeständnis: {df_urteil['gestaendnis']}" \
                    f"\n\n{df_urteil['id']}"
    return urteil_auszug


# Plot Selection
@app.callback(
    Output('selected-data', 'children'),
    [Input('basic-interactions', 'selectedData')])
def display_selected_data(selectedData):
    return json.dumps(selectedData, indent=2)


# Plot Zoom
@app.callback(
    Output('relayout-data', 'children'),
    [Input('basic-interactions', 'relayoutData')])
def display_relayout_data(relayoutData):
    x_range_from = relayoutData['xaxis.range[0]']
    x_range_to = relayoutData['xaxis.range[1]']
    y_range_from = relayoutData['yaxis.range[0]']
    y_range_to = relayoutData['yaxis.range[1]']
    return json.dumps(relayoutData, indent=2)


""" -- Callbacks -- """


# Tabs
@app.callback([Output('first_tab', 'style'),
               Output('second_tab', 'style'),
               Output('menu', 'style')],
              [Input('tabs-example', 'value')])
def render_content(tab):
    # --- Graph and Table ---
    if tab == 'tab-1':
        return {'display': 'block'}, {'display': 'none'}, {'background-color': '#E8E8E8', "padding": "15px", }

    # --- Full Text Search ---
    elif tab == 'tab-2':
        return {'display': 'none'}, {'display': 'block'}, {'opacity': '80%', "color": "grey", "padding": "15px", }


# Graph and Table callback
@app.callback(
    # output both graph and table
    [Output('basic-interactions', 'figure'),
     Output('table_div', 'children')],
    # use button or plot zoom as input event
    [Input("suchen", "n_clicks")],
    # use dropdown, both checkboxes and slider as input
    [State('volltext_id', 'value'),
     State('gericht', 'value'),
     State('vorstr_checkbox', 'value'),
     State('vorstr', 'value'),
     State('gest_checkbox', 'value'),
     State('gest', 'value'),
     State('slider_min', 'value'),
     State('slider_max', 'value'),
     State('my-date-picker-range', 'start_date'),
     State('my-date-picker-range', 'end_date')])
def update_graph_and_table(n, volltext_id, gericht, vorstr_checkbox, vorstr, gest_checkbox, gest,
                           slider_min, slider_max, start_date, end_date):
    # if the dropdown doesn't contain search arguments: show all
    if gericht is None or len(gericht) == 0:
        dff = urteile_df
    else:
        dff = urteile_df[urteile_df['gericht'].isin(gericht)]

    # look for id
    if volltext_id is None or len(volltext_id) == 0:
        pass
    else:
        dff = dff[dff['id'].str.match('.*' + volltext_id + '.*')]

    # if Vorstrafen are checked, filter output
    if vorstr_checkbox:
        df_select = dff[(dff.vorstrafe == vorstr)]
    else:
        df_select = dff

    # if Geständnis is checked, filter output again
    if gest_checkbox:
        df_select = df_select[(dff.gestaendnis == gest)]
    else:
        pass

    # filter output by Schadenshöhe range
    df_select = df_select[(df_select['schaden'] >= slider_min) & (df_select["schaden"] <= slider_max)]

    # filter by date
    df_select = df_select[(df_select['date'] >= start_date) & (df_select['date'] <= end_date)]

    ### zoom output
    # todo: connect graph and table

    """print(len(relayoutData))
    if len(relayoutData) > 1 or relayoutData['autosize'] is False:
        x_range_from = relayoutData['xaxis.range[0]']
        x_range_to = relayoutData['xaxis.range[1]']
        y_range_from = relayoutData['yaxis.range[0]']
        y_range_to = relayoutData['yaxis.range[1]']

        df_select = df_select[(df_select['schaden'] <= x_range_to) & (df_select['schaden'] >= x_range_from)]
        df_select = df_select[(df_select['strafmass_tagessatz'] <= y_range_to) & (df_select['strafmass_tagessatz'] >= y_range_from)]"""

    ###

    # return a graph and a table
    return (
        {
            'data': [
                dict(
                    x=df_select[df_select["gericht"] == i]['schaden'],
                    y=df_select[df_select["gericht"] == i]['strafmass_tagessatz'],
                    text=df_select[df_select["gericht"] == i]['gericht'] + " " + df_select[df_select["gericht"] == i][
                        'id'],
                    mode='markers',
                    marker={
                        'size': 15,
                        'opacity': 0.5,
                        'line': {'width': 0.5, 'color': 'white'},
                    },
                    name=i
                ) for i in df_select.gericht.unique()
            ],
            'layout': dict(
                xaxis={
                    'title': "Schadenshöhe in Euro",
                },
                yaxis={
                    'title': "Anzahl Tagessätze",
                },
                margin={'l': 40, 'b': 40, 't': 10, 'r': 0},
                hovermode='closest'
            )
        },
        html.Div(
            [
                dash_table.DataTable(
                    id="dash_table",
                    columns=[{"name": e, "id": i} for e, i in
                             zip(["Datum", "Gericht", "Delikt", "Vorstrafen", "Geständnis", "Schaden", "Höhe",
                                  "Tagessatz", "Volltext-ID"], df_select.columns)],
                    data=df_select.to_dict('records'),
                    page_current=0,
                    page_size=15,
                    page_action='native',
                    sort_action="native",
                    style_cell_conditional=[
                        {
                            'if': {'column_id': c},
                            'textAlign': 'left'
                        } for c in ['Date', 'Region']
                    ],
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)',
                            'if': {'column_id': 'strafmass_tagessatz'},
                            'backgroundColor': 'rgb(255, 102, 102)',
                        }
                    ],
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                    }
                ),
            ]
        )
    )


# Reset
@app.callback(
    [Output('volltext_id', 'value'),
     Output('gericht', 'value'),
     Output('vorstr_checkbox', 'value'),
     Output('gest_checkbox', 'value'),
     Output('slider_min', 'value'),
     Output('slider_max', 'value'),
     Output('delikt', 'value'),
     Output('my-date-picker-range', 'start_date'),
     Output('my-date-picker-range', 'end_date')],
    [Input("reset", "n_clicks")])
def update_graph_and_table(n):
    return '', None, False, False, 0, 500, None, dt(1950, 1, 1).date(), dt(2020, 1, 1).date()
# tart_date=dt(1950, 1, 1).date(),
#                         end_date=dt(2020, 1, 1).date()


# Average Table callback
@app.callback(
    Output('average', 'children'),
    [Input('dash_table', 'data')])
def calculate_average(data):
    temp_df = pd.DataFrame(data=data, columns=data[0].keys())
    d = {'Schaden': int(temp_df["schaden"].mean()), 'Betrag': int(temp_df["strafmass_betrag"].mean()),
         'Tagessatz': int(temp_df["strafmass_tagessatz"].mean())}
    average_df = pd.DataFrame(data=d, index=[1])
    return html.Div(
        [
            dash_table.DataTable(
                id="dash_table",
                columns=[{"name": e, "id": i} for e, i in
                         zip(["Ø Schaden", "Ø Betrag", "Ø Tagessatz"],
                             average_df.columns)],
                data=average_df.to_dict('records'),
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                }
            ),
        ]
    )


# Full Text callback
@app.callback(
    Output('id_output', 'children'),
    [Input('id_input', 'value')],
    [State('id_output', 'children')])
def show_hide_element(id_input, children):
    children = []
    for urteil_id in urteile_df["id"]:
        if id_input in urteil_id:
            row = urteile_df[urteile_df["id"].str.match(urteil_id)]

            volltext = row["body"]
            el = html.Div(children=[
                html.Hr(),
                dbc.Col([
                    html.Div(row["id"], style={"font-weight": "bold"}),
                    html.Br(),
                    html.Div(row["date"]),
                    html.Div(row["gericht"]),
                    html.Br(),
                    html.Div("Delikt: " + row["delikt"]),
                    html.Div("Vorstrafen: " + row["vorstrafe"]),
                    html.Div("Geständnis: " + row["gestaendnis"]),
                    html.Div("Schaden: " + row["schaden"].to_string()[2:]),
                    html.Div("Strafmaß: " + row["strafmass_tagessatz"].to_string()[2:] + " Tagessätze zu je "
                             + row["strafmass_betrag"].to_string()[2:] + " Euro"),
                ], style={"font-size": "12px"}),
                html.Br(),
                dbc.Col([
                    html.Pre(volltext, style={"border-style": "solid", "padding": "15px", "padding-right": "10px",
                                              "border-width": "thin"}),
                ], width=12),
                html.Hr(),
            ], style={"margin": "20px", "font-size": "12px"})

            children.append(el)
    return children


# Vorstrafen callback
@app.callback(
    Output(component_id='vorstr', component_property='style'),
    [Input(component_id='vorstr_checkbox', component_property='value')])
def show_hide_element(visibility_state):
    if visibility_state:
        return {'display': 'block'}
    else:
        return {'display': 'none'}


# Geständnis callback
@app.callback(
    Output(component_id='gest', component_property='style'),
    [Input(component_id='gest_checkbox', component_property='value')])
def show_hide_element(visibility_state):
    if visibility_state:
        return {'display': 'block'}
    else:
        return {'display': 'none'}


# Toggle callback
@app.callback(
    [Output(component_id='basic-interactions', component_property='style'),
     Output(component_id="Switchin", component_property="style")],
    [Input(component_id='map_toggle', component_property='value')])
def show_hide_element(umschalten):
    if umschalten:
        return {'display': 'none'}, {'display': 'block'}
    else:
        return {'display': 'block'}, {'display': 'none'}


# Driver
if __name__ == '__main__':
    app.run_server(debug=False)

"""


# Slider callback (cannot be used with number input - circular dependencies)
dcc.RangeSlider(
                            id='range-slider',
                            marks={
                                0: {'label': '0'},
                                500: {'label': '500'},
                                1000: {'label': '1000'},
                                1500: {'label': '1500'},
                                2000: {'label': '2000'},
                                2500: {'label': f'{urteile_df["schaden"].max()}', 'style': {'color': '#f50'}},
                            },
                            value=[0, 500],
                            min=0,
                            max=urteile_df["schaden"].max(),

                        ),

@app.callback(
    [Output('output-container-range-slider', 'children'),
     Output('slider_min', 'value'),
     Output('slider_max', 'value')],
    [Input('range-slider', 'value')])
def update_output(value):
    return ('Auswahl: {}'.format(value),
            value[0],
            value[1])





#layout
dash_table.DataTable(
                    id="dash_table",
                    columns=[{"name": e, "id": i} for e, i in
                             zip(["Datum", "Gericht", "Tagessatz", "Betrag", "Schaden", "Vorstrafen", "Geständnis"],
                                 urteile_df.columns)],
                    data=urteile_df.to_dict('records')
                ),
                # table
                dbc.Row(
                    dbc.Col(html.Table(id='table'), width=12),
                ),

#callback
return html.Table([
        html.Thead(
            html.Tr([html.Th(col) for col in
                     ["Gericht", "Date", "Tagessatz", "Betrag", "Schaden", "Vorstrafe", "Geständnis"]])
        ),
        html.Tbody([
            html.Tr([
                html.Td(df_select.iloc[i][col]) for col in df_select.columns
            ]) for i in range(min(len(df_select), 25))
        ])
    ])







@app.callback(
    Output(component_id='my-div', component_property='children'),
    [Input(component_id='my-id', component_property='value')]
)
def update_output_div(input_value):
    return 'You\'ve entered "{}"'.format(input_value)"""

"""

html.Div([

        html.Div([
            dcc.Dropdown(
                id='xaxis-column',
                options=[{'label': i, 'value': i} for i in gerichte_namen],
                value='Amtsgericht Leipzig',
            ),
            html.P(children="Vorstrafen"),
            dcc.RadioItems(
                id='vorstr',
                options=[{'label': i, 'value': i} for i in ['Ja', 'Nein']],
                value='Ja',
                labelStyle={'display': 'inline-block'}
            ),
            html.P(children="Geständnis"),
            dcc.RadioItems(
                id='gest',
                options=[{'label': i, 'value': i} for i in ['Ja', 'Nein']],
                value='Ja',
                labelStyle={'display': 'inline-block'}
            ),
        ],
            style={'width': '48%',
                   'display': 'inline-block',
                   'top': 0
                   }, className="m-5"),

        html.Div([

            #dcc.Graph(id='indicator-graphic'),
            #html.Table(id='table'),

        ],
            style={'width': '48%',
                   'display': 'inline-block',
                   }),

    ]),

# -- old stuff --
    html.H4(children='Strafurteile Amtsgerichte'),
    dcc.Input(id='my-id', value='Amtsgericht Bremen', type='text'),
    html.Div(id='my-div'),
    # dcc.Graph(id='graph-with-slider'),
    dcc.Graph(
        id='urteil_graph',
        figure={
            'data': [
                dict(
                    x=urteile_df[urteile_df['gericht'] == i]['schaden'],
                    y=urteile_df[urteile_df['gericht'] == i]['strafmass_tagessatz'],
                    mode='markers',
                    opacity=0.7,
                    marker={
                        'size': 15,
                        'line': {'width': 0.5, 'color': 'white'}
                    },
                    name=i
                ) for i in urteile_df.gericht.unique()
            ],
            'layout': dict(
                xaxis={'type': 'log', 'title': 'Schaden'},
                yaxis={'title': 'Tagessatz'},
                margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
                legend={'x': 0, 'y': 1},
                hovermode='closest'
            )
        },
    ),
    generate_table(urteile_df),
    """

# todo: testing!
"""@app.callback(
    Output(component_id='graph-with-slider', component_property='figure'),
    [Input(component_id='my-id', component_property='value')]
)
def update_figure(input_text):
    print(input_text)
    filtered_df = urteile_df[urteile_df["gericht"].isin([input_text])]
    traces = []
    for i in filtered_df.gericht.unique():
        df_by_gericht = filtered_df[filtered_df['gericht'] == i]
        traces.append(dict(
            x=df_by_gericht['schaden'],
            y=df_by_gericht['strafmass_tagessatz'],
            text=df_by_gericht['gericht'],
            mode='markers',
            opacity=0.7,
            marker={
                'size': 15,
                'line': {'width': 0.5, 'color': 'white'}
            },
            name=i
        ))

    print(df_by_gericht)
    return {
        'data': traces,
        'layout': dict(
            xaxis={'type': 'log', 'title': 'Schaden'},
            yaxis={'title': 'Tagessatz'},
            margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
            legend={'x': 0, 'y': 1},
            hovermode='closest',
            transition = {'duration': 500},
        )
    }"""

"""
# ganzer Graph
dcc.Graph(
            id='life-exp-vs-gdp',
            figure={
                'data': [
                    dict(
                        x=df[df['continent'] == i]['gdp per capita'],
                        y=df[df['continent'] == i]['life expectancy'],
                        text=df[df['continent'] == i]['country'],
                        mode='markers',
                        opacity=0.7,
                        marker={
                            'size': 15,
                            'line': {'width': 0.5, 'color': 'white'}
                        },
                        name=i
                    ) for i in df.continent.unique()
                ],
                'layout': dict(
                    xaxis={'type': 'log', 'title': 'GDP Per Capita'},
                    yaxis={'title': 'Life Expectancy'},
                    margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
                    legend={'x': 0, 'y': 1},
                    hovermode='closest'
                )
            }
        ),
"""

"""# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

colors = {
    'background': '#111111',
    'text': '#7FDBFF'
}

app.layout = html.Div(style={'backgroundColor': colors['background']}, children=[
    html.H1(
        children='Hello Dash',
        style={
            'textAlign': 'center',
            'color': colors['text']
        }
    ),

    html.Div(children='Dash: A web application framework for Python.', style={
        'textAlign': 'center',
        'color': colors['text']
    }),

    dcc.Graph(
        id='example-graph-2',
        figure={
            'data': [
                {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
                {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
            ],
            'layout': {
                'plot_bgcolor': colors['background'],
                'paper_bgcolor': colors['background'],
                'font': {
                    'color': colors['text']
                }
            }
        }
    )
])

if __name__ == '__main__':
    app.run_server(debug=True)"""
