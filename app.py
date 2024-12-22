from flask import Flask
import requests
import dash
from dash import dcc, html, Input, Output, State, callback, MATCH
import pandas as pd
import plotly.graph_objects as go

api_key = 'zGREiPFDIlupJNg9nFmsMlQtCVnwQj7p'

server = Flask(__name__)

def fetch_location_key(city_name):
    url = f'http://dataservice.accuweather.com/locations/v1/cities/search?apikey={api_key}&q={city_name}'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return [data[0]['Key'], data[0]["GeoPosition"]["Latitude"], data[0]["GeoPosition"]["Longitude"]] if data else None
    except requests.exceptions.RequestException as ex:
        print(f"Ошибка при запросе данных для города '{city_name}': {ex}")
        return None
    # return "ok"

def fetch_daily_forecast(location_id):
    url = f"http://dataservice.accuweather.com/forecasts/v1/daily/5day/{location_id}?apikey={api_key}&details=true&metric=true"
    try:
        response = requests.get(url)
        response.raise_for_status()
        forecast = response.json()
        return forecast['DailyForecasts'] if 'DailyForecasts' in forecast else None
    except requests.exceptions.RequestException as ex:
        print(f"Ошибка получения прогноза: {ex}")
        return None
    # with open('weather_first.json', 'r') as f:
    #     forecast = json.load(f)
    #     return forecast

def get_graph(data, type, days=5):
    df = pd.DataFrame([{
        'time': item['Date'][:10],
        'temperature': item['Temperature']['Maximum']['Value'],
        'wind_speed': item['Day']['Wind']['Speed']['Value'],
        'precipitation_probability': item['Day']['PrecipitationProbability']
    } for item in data])

    df = df.iloc[:days]
    
    fig = go.Figure()
    if type == 'Температура':
        fig.add_trace(go.Scatter(x=df['time'], y=df['temperature'], mode='lines+markers', name='Temperature (°C)'))
        fig.update_layout(title='Hourly Temperature', xaxis_title='Day', yaxis_title='Temperature (°C)')
    elif type == 'Скорость ветра':
        fig.add_trace(go.Scatter(x=df['time'], y=df['wind_speed'], mode='lines+markers', name='Wind Speed (m/s)'))
        fig.update_layout(title='Hourly Wind Speed', xaxis_title='Day', yaxis_title='Wind Speed (m/s)')
    elif type == 'Вероятность осадков':
        fig.add_trace(go.Scatter(x=df['time'], y=df['precipitation_probability'], mode='lines+markers', name='Precipitation Probability (%)'))
        fig.update_layout(title='Hourly Precipitation Probability', xaxis_title='Day', yaxis_title='Probability (%)')
    fig.update_layout(
    template='simple_white',
    font=dict(
        size=14,
        color="#003366"
    ),
    title_font=dict(
        size=20,
        color="#003366"
    ),
    xaxis=dict(
        linecolor="#003366",
        gridcolor="#d0e7ff",
        tickfont=dict(size=12, color="#003366")
    ),
    yaxis=dict(
        linecolor="#003366",
        gridcolor="#d0e7ff",
        tickfont=dict(size=12, color="#003366")
    )
)

    return fig

def get_map():
    global cities
    latitudes = [point["lat"] for point in cities]
    longitudes = [point["lon"] for point in cities]

    fig = go.Figure()

    # Добавление точек и маршрутов
    fig.add_trace(go.Scattergeo(
        lat=latitudes,
        lon=longitudes,
        mode='markers+lines',
        marker=dict(
            size=10,
            color='red',
            symbol='circle',
            line=dict(width=1, color='white')
        ),
        line=dict(width=2, color='blue'),
        name='Маршрут'
    ))

    # Настройки оформления карты
    fig.update_layout(
        title=dict(
            text='Маршрут по городам',
            font=dict(size=24, color='#003366'),
            x=0.5
        ),
        showlegend=True,
        legend=dict(
            font=dict(size=12, color='#003366'),
            bgcolor='rgba(240, 248, 255, 0.8)',  # Полупрозрачный фон легенды
            bordercolor='#003366',
            borderwidth=1
        ),
        geo=dict(
            resolution=50,
            showland=True,
            landcolor='rgb(217, 217, 217)',
            showocean=True,
            oceancolor='rgb(230, 245, 255)',
            showcountries=True,
            countrycolor='rgb(204, 204, 204)',
            showlakes=True,
            lakecolor='rgb(200, 240, 255)',
            coastlinecolor='rgb(51, 102, 204)',
            projection=dict(
                type='equirectangular'  # Или выберите другой, например, 'mercator'
            ),
            lataxis=dict(
                range=[min(latitudes) - 10, max(latitudes) + 10],
                showgrid=True,
                gridcolor='rgb(200, 220, 255)',
                dtick=10
            ),
            lonaxis=dict(
                range=[min(longitudes) - 20, max(longitudes) + 20],
                showgrid=True,
                gridcolor='rgb(200, 220, 255)',
                dtick=20
            ),
        ),
        margin=dict(
            r=10, t=40, l=10, b=10  # Уменьшение отступов
        ),
        paper_bgcolor='rgb(240, 248, 255)'  # Светлый синий фон
    )

    return fig


app = dash.Dash(name="weather")
app.layout = html.Div(children=[
    html.H1(children='Прогноз погоды'),

    html.Div(id='cities', children=[
        dcc.Input(id={'type': 'city', 'index' : '1'}, type='text', placeholder='Начальный город'),
        dcc.Input(id={'type': 'city', 'index' : '2'}, type='text', placeholder='Конечный город'),
]),
    html.Button('Добавить промежуточный город', id='new_city_btn', n_clicks=0),
    html.Button('Получить прогноз погоды', id='submit-val', n_clicks=0),
    html.Div(id='container-button-basic',children=[]),
])

cities = []

@callback(
    Output('container-button-basic', 'children'),
    Input('submit-val', 'n_clicks'),
    State('cities', 'children'),
    prevent_initial_call=True
)
def update_output(n_clicks, cities_input):
    data = []
    global cities
    cities = []
    cities_name = [x['props']['value'] for x in cities_input if x['props']['value'] != None]
    last_city = cities_name[1]
    cities_name.remove(last_city)
    cities_name.append(last_city)
    if len(cities_name) >= 2 and n_clicks > 0:
        for city in cities_name:
            loc = fetch_location_key(city)
            if loc:
                weather = fetch_daily_forecast(loc[0])
                if weather:
                    graph = get_graph(weather, "Температура")
                    cities.append({"name": city, "loc_key": loc[0], "lat": loc[1], "lon": loc[2], "weather": weather })

                    data.append(html.H2(children=f'График города {city}'))
                    data.append(dcc.RadioItems(id={'type': 'graph-type', 'index':len(cities) },options=[{'label': i, 'value': i} for i in ['Температура', 'Скорость ветра', 'Вероятность осадков']],value='Температура', style={"display": "inline-block"}))
                    data.append(dcc.Slider(id={'type':'day-slider', 'index': len(cities)},min=1,max=5,marks={1: '1', 2: '2', 3: '3', 4: '4', 5: '5'}, value=5,step=None))
                    data.append(dcc.Graph(id={'type': 'graph', 'index': len(cities)}, figure=graph))
                    data.append(html.Div(id={'type': 'graph-index', 'index':len(cities)},children= f'{len(cities)}'))

                else:
                    return f"Не удалось получить погоду {city}"
            else:
                return f"Не удалось найти город {city}"
        data.append(dcc.Graph(id='map', figure=get_map()))
    else:
        return "Заполните пустые поля"
    return data

@callback(
    Output({'type': 'graph', 'index': MATCH}, 'figure'),
    Input({'type': 'graph-type', 'index': MATCH}, 'value'),
    Input({'type': 'day-slider', 'index': MATCH}, 'value'),
    State({'type': 'graph-index', 'index': MATCH}, 'children')

)
def update_graph(graph_types, days, graph_index):
    graph = get_graph(cities[int(graph_index)-1]['weather'], graph_types, days)
    return graph
    
@callback(
    Output('cities', 'children'),
    Input('new_city_btn', 'n_clicks'),
    State('cities', 'children')
)
def new_city(n_clicks, cities):
    if n_clicks > 0:
        cities.append(dcc.Input(id={'type': 'city', 'index' : len(cities)}, type='text', placeholder='Промежуточный город'))
        return cities
    else:
        return cities


if __name__ == '__main__':
    app.run_server(debug=True)
