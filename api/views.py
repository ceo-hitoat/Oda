from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry

class CoordinatesReturnView(APIView):

    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    api_key = "AIzaSyD7j2O97-15Ci47KiNZtocbztuQLRJduYs" 
    
    def get(self, request):
        try:
            params = {
                "address": request.query_params.get("eircode"),
                "region": "ie",  
                "key": self.api_key
            }
            print("no problem here")

            response = requests.get(self.base_url, params=params)
            print("problem here", response.content)
            response.raise_for_status()  

            data = response.json()
            if data['status'] == "OK":
                location = data["results"][0]["geometry"]["location"]  
                lat = location['lat']
                lon = location['lng']
                print("no problem here", lat, lon)
                return Response({"coordinates": {"latitude": lat, "longitude": lon}}, status=status.HTTP_200_OK)
            else:
                return Response({"error message": data["status"]}, status=status.HTTP_404_NOT_FOUND)

        except requests.exceptions.RequestException as e:
            return Response({"error message": f"Request failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except KeyError:
            return Response({"error message": "Invalid response format from API"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error message": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AnalyticsView(APIView):

    try:
        cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
        retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
        openmeteo = openmeteo_requests.Client(session = retry_session)

        meteo_url = "https://api.open-meteo.com/v1/forecast"

        # Moderate values for each variable
        MODERATE_VALUES = {
            "temperature_2m": 14,  # [5 to 40 ]
            "relative_humidity_2m": 65, # [ 45 to 100]
            "dew_point_2m": 6, # [4 to 10]
            "cloud_cover": 50, # [0 to 100]
            "wind_direction_10m": 180, # [0 to 360]
            "wind_gusts_10m": 80 # [0 to 100]
        }

        # Define ranges for each variable
        RANGES = {
            "temperature_2m": (0, 40),
            "relative_humidity_2m": (45, 100),
            "dew_point_2m": (4, 10),
            "cloud_cover": (0, 100),
            "wind_direction_10m": (0, 360),
            "wind_gusts_10m": (0, 100),
        }   

        def post(self, request):

            try:

                latitude = request.data.get("latitude")
                longitude = request.data.get("longitude")
                hourly_variables = request.data.get("hourly")
                forecast_days = request.data.get("forecast_days")
                print("latitude", latitude, "longitude", longitude, "forecast_days", forecast_days, "hourly_variables", hourly_variables)

                if (latitude and longitude) and (hourly_variables and forecast_days):

                    params = {
                        "latitude": latitude,
                        "longitude": longitude,
                        "hourly": hourly_variables,
                        "forecast_days": forecast_days,
                        "daily": "sunshine_duration",
                        "timezone": "Europe/London"
                    }

                    try:
                        responses = self.openmeteo.weather_api(self.meteo_url, params)

                        response = responses[0]

                        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
                        print(f"Elevation {response.Elevation()} m asl")
                        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
                        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

                        # Process hourly data. The order of variables needs to be the same as requested.
                        hourly = response.Hourly()
                    
                        dates = pd.date_range(
                            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                            freq=pd.Timedelta(seconds=hourly.Interval()),
                            inclusive="left"
                        ).tolist()

                        response_data = {
                            "data": {
                                "date": [date.isoformat() for date in dates],
                                "variables": {}
                            }
                        }    

                        # update moderate values
                        updated_values = self.MODERATE_VALUES.copy()

                        # for key, new_value in moderate_value_array.items():
                        #     if key in self.RANGES:
                        #         min_val, max_val = self.RANGES[key]
                        #         # Check if the new value is within the defined range
                        #         if min_val <= new_value <= max_val:
                        #             updated_values[key] = new_value  # Replace with the new value                  
                                        
                        for idx, variable in enumerate(hourly_variables):
                            variable_values = hourly.Variables(idx).ValuesAsNumpy()

                            print("variable_values:", variable, variable_values)


                            # Get moderate value for the variable
                            moderate_value = updated_values.get(variable, None)

                            print("moderate_value:", moderate_value)

                            working_hours = 0
                            electricity_providers = {
                                   "Electric Ireland": 0.42, # cents per kwh
                                   "Bord Gais Energy": 0.43,
                                   "SSE Airtricity": 0.43,
                                   "Energia": 0.38,
                                   "PrePayPower": 0.46,
                                   "Flogas": 0.43
                                   }
                            
                            electricity_total_rate_per_brand = {}    

                            average_consumption_per_hour = 0.48 # kwh                     

                            # Calculate working hours: values greater than the moderate value
                            if moderate_value is not None:
                                for values in variable_values:
                                    if values < moderate_value:
                                        working_hours += 1
                            else:
                                working_hours = None  # If no moderate value exists, skip this step

                            if working_hours is not None:
                                total_kwh = working_hours * average_consumption_per_hour

                                for idx, value in electricity_providers.items():
                                    electricity_total_rate_per_brand[idx] = round((total_kwh * value), 2)

                            print("working_hours:", working_hours)

                            # Add variable data to the response
                            response_data["data"]["variables"][variable] = {
                                "values": variable_values.tolist(),  # Convert numpy array to list
                                "moderate_value": moderate_value,
                                "working_hours": working_hours,
                                "electricity_total_rate_per_brand": electricity_total_rate_per_brand
                            }

                        # Return the JSON response
                        return Response(response_data, status=status.HTTP_200_OK)
                    except Exception as e:
                        print(f"Error message: {str(e)}")
                        return Response({"error message": "Check the parameters"}, status=status.HTTP_404_NOT_FOUND)
                else:
                    return Response({"message": "Check the parameters send"}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                print(f"Error message: {str(e)}", )
                return Response({"error message": "Check the coordinates value"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print({"error": f"An unexpected error occured, {str(e)}"})
        
     