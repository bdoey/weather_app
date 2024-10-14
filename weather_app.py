import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import openmeteo_requests
import requests_cache
from retry_requests import retry

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

def fetch_weather_data(latitude, longitude, start_date, end_date):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": (end_date + timedelta(days=1)).strftime("%Y-%m-%d"),
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "windspeed_10m_max", "relative_humidity_2m_max"],
        "timezone": "America/Chicago"
    }
    
    try:
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        
        daily = response.Daily()
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")
        
        daily_data = {
            "date": date_range,
            "temperature_max": daily.Variables(0).ValuesAsNumpy()[:len(date_range)],
            "temperature_min": daily.Variables(1).ValuesAsNumpy()[:len(date_range)],
            "precipitation": daily.Variables(2).ValuesAsNumpy()[:len(date_range)],
            "windspeed_max": daily.Variables(3).ValuesAsNumpy()[:len(date_range)],
            "humidity_max": daily.Variables(4).ValuesAsNumpy()[:len(date_range)]
        }
        
        for key in daily_data:
            if key != "date" and len(daily_data[key]) < len(date_range):
                daily_data[key] = np.pad(daily_data[key], (0, len(date_range) - len(daily_data[key])), 'constant', constant_values=np.nan)
        
        return pd.DataFrame(daily_data)
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return pd.DataFrame()

# Streamlit app
st.title("Weather Comparison: Dallas vs Orlando vs Omaha")

# Date range selection
st.sidebar.header("Select Date Range")
end_date = datetime.now().date() - timedelta(days=2)  # Yesterday
start_date = end_date - timedelta(days=30)  # Default to last 30 days
date_range = st.sidebar.date_input("Date range", [start_date, end_date])

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    st.warning("Please select both start and end dates.")
    st.stop()

# Fetch data for all three cities
st.info("Fetching weather data...")
dallas_data = fetch_weather_data(32.7767, -96.7970, start_date, end_date)
orlando_data = fetch_weather_data(28.5383, -81.3792, start_date, end_date)
omaha_data = fetch_weather_data(41.2565, -95.9345, start_date, end_date)

# Check if data is empty or has any NaN values
if dallas_data.empty or orlando_data.empty or omaha_data.empty:
    st.error("No data available for the selected date range. Please try a different range.")
    st.stop()

# if dallas_data.isna().any().any() or orlando_data.isna().any().any() or omaha_data.isna().any().any():
#     st.warning("Some data points are missing. The visualization may be incomplete.")

# Create comparison plots
fig = make_subplots(rows=3, cols=1, subplot_titles=("Temperature", "Precipitation", "Wind Speed"))

# Temperature plot
fig.add_trace(go.Scatter(x=dallas_data['date'], y=dallas_data['temperature_max'], name="Dallas Max Temp", line=dict(color="red")), row=1, col=1)
# fig.add_trace(go.Scatter(x=dallas_data['date'], y=dallas_data['temperature_min'], name="Dallas Min Temp", line=dict(color="blue")), row=1, col=1)
fig.add_trace(go.Scatter(x=orlando_data['date'], y=orlando_data['temperature_max'], name="Orlando Max Temp", line=dict(color="orange")), row=1, col=1)
# fig.add_trace(go.Scatter(x=orlando_data['date'], y=orlando_data['temperature_min'], name="Orlando Min Temp", line=dict(color="lightblue")), row=1, col=1)
fig.add_trace(go.Scatter(x=omaha_data['date'], y=omaha_data['temperature_max'], name="Omaha Max Temp", line=dict(color="green")), row=1, col=1)
# fig.add_trace(go.Scatter(x=omaha_data['date'], y=omaha_data['temperature_min'], name="Omaha Min Temp", line=dict(color="lightgreen")), row=1, col=1)

# Precipitation plot
fig.add_trace(go.Bar(x=dallas_data['date'], y=dallas_data['precipitation'], name="Dallas Precipitation", marker_color="red"), row=2, col=1)
fig.add_trace(go.Bar(x=orlando_data['date'], y=orlando_data['precipitation'], name="Orlando Precipitation", marker_color="orange"), row=2, col=1)
fig.add_trace(go.Bar(x=omaha_data['date'], y=omaha_data['precipitation'], name="Omaha Precipitation", marker_color="green"), row=2, col=1)

# Wind Speed plot
fig.add_trace(go.Scatter(x=dallas_data['date'], y=dallas_data['windspeed_max'], name="Dallas Wind Speed", line=dict(color="red")), row=3, col=1)
fig.add_trace(go.Scatter(x=orlando_data['date'], y=orlando_data['windspeed_max'], name="Orlando Wind Speed", line=dict(color="orange")), row=3, col=1)
fig.add_trace(go.Scatter(x=omaha_data['date'], y=omaha_data['windspeed_max'], name="Omaha Wind Speed", line=dict(color="green")), row=3, col=1)

fig.update_layout(height=900, width=800, title_text="Weather Comparison: Dallas vs Orlando vs Omaha")
fig.update_xaxes(title_text="Date", row=3, col=1)
fig.update_yaxes(title_text="Temperature (°C)", row=1, col=1)
fig.update_yaxes(title_text="Precipitation (mm)", row=2, col=1)
fig.update_yaxes(title_text="Wind Speed (km/h)", row=3, col=1)

st.plotly_chart(fig)

# Display average statistics
st.subheader("Average Weather Statistics")
col1, col2, col3 = st.columns(3)

with col1:
    st.write("Dallas Averages:")
    st.write(f"Avg Max Temp: {dallas_data['temperature_max'].mean():.1f}°C")
    st.write(f"Avg Min Temp: {dallas_data['temperature_min'].mean():.1f}°C")
    st.write(f"Avg Precipitation: {dallas_data['precipitation'].mean():.1f}mm")
    st.write(f"Avg Max Wind Speed: {dallas_data['windspeed_max'].mean():.1f}km/h")
    st.write(f"Avg Max Humidity: {dallas_data['humidity_max'].mean():.1f}%")

with col2:
    st.write("Orlando Averages:")
    st.write(f"Avg Max Temp: {orlando_data['temperature_max'].mean():.1f}°C")
    st.write(f"Avg Min Temp: {orlando_data['temperature_min'].mean():.1f}°C")
    st.write(f"Avg Precipitation: {orlando_data['precipitation'].mean():.1f}mm")
    st.write(f"Avg Max Wind Speed: {orlando_data['windspeed_max'].mean():.1f}km/h")
    st.write(f"Avg Max Humidity: {orlando_data['humidity_max'].mean():.1f}%")

with col3:
    st.write("Omaha Averages:")
    st.write(f"Avg Max Temp: {omaha_data['temperature_max'].mean():.1f}°C")
    st.write(f"Avg Min Temp: {omaha_data['temperature_min'].mean():.1f}°C")
    st.write(f"Avg Precipitation: {omaha_data['precipitation'].mean():.1f}mm")
    st.write(f"Avg Max Wind Speed: {omaha_data['windspeed_max'].mean():.1f}km/h")
    st.write(f"Avg Max Humidity: {omaha_data['humidity_max'].mean():.1f}%")

# st.write("Data source: [Open-Meteo](https://open-meteo.com)")
