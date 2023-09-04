import os
import cv2
import time
import folium
import numpy as np
import geopandas as gpd
from geopy import exc
from selenium import webdriver
from unidecode import unidecode
from geopy.geocoders import Nominatim
from shapely.geometry import Polygon, shape


def pobierz_granice_miasta(nazwa_miasta):
    geolokalizator = Nominatim(user_agent="moj_program")
    try:
        lokalizacja = geolokalizator.geocode(nazwa_miasta, geometry="geojson")
        województwo = (
            lokalizacja.raw["display_name"].split("województwo ")[1].split(",")[0]
        )
        granice = lokalizacja.raw["geojson"]["coordinates"][0]
        return granice, województwo, lokalizacja.raw["lon"], lokalizacja.raw["lat"]
    except (exc.GeocoderTimedOut, IndexError):
        print("Nie można pobrać danych o granicach miasta.")
        return None


nazwa_miasta = input("Nazwa miasta")

granice_miasta = pobierz_granice_miasta(nazwa_miasta)


# Przykładowe użycie funkcji
def tworzenie_obrazu_z_mapy():
    if granice_miasta:
        if type(granice_miasta[0]) == list:
            if len([*granice_miasta[0]]) > 4:
                geojson_data = {
                    "type": "Polygon",
                    "coordinates": [[[lon, lat] for lon, lat in granice_miasta[0]]],
                }
                # Create a Folium map
                mapa = folium.Map(
                    location=[granice_miasta[3], granice_miasta[2]], zoom_start=11
                )
                granice_miasta_coords = granice_miasta[0]
                # Znajdź minimalne i maksymalne wartości szerokości i długości geograficznej
                min_lon = min(lon for lon, lat in granice_miasta_coords)
                max_lon = max(lon for lon, lat in granice_miasta_coords)
                min_lat = min(lat for lon, lat in granice_miasta_coords)
                max_lat = max(lat for lon, lat in granice_miasta_coords)

                # Utwórz granice w formie listy [(min_lat, min_lon), (max_lat, max_lon)]
                bounds = [(min_lat, min_lon), (max_lat, max_lon)]
                mapa.fit_bounds(bounds=bounds, padding=0)
                # Add the choropleth map overlay
                folium.GeoJson(
                    geojson_data,
                    name="Choropleth Map",
                    style_function=lambda x: {"fillColor": "red", "color": "red"},
                ).add_to(mapa)
                gdf = gpd.GeoDataFrame(
                    {"geometry": [shape(geojson_data)]}, crs="EPSG:4326"
                )

                mapa.save("mapa.html")
                mapa_html = "mapa.html"
                mapa_png = "mapa.png"

                # Konwersja pliku HTML na obrazek PNG za pomocą Selenium
                options = webdriver.ChromeOptions()
                options.add_argument(
                    "--headless"
                )  # Opcjonalnie, jeśli nie chcesz widocznego okna przeglądarki
                driver = webdriver.Chrome(options=options)
                driver.get(f"file://{os.path.abspath(mapa_html)}")

                time.sleep(4)
                driver.save_screenshot(mapa_png)
                driver.quit()
            else:
                print("Sory, Your city have no data in our database")
        else:
            print("Sory, Your city have no data in our database")


def maskowanie():
    image = cv2.imread("mapa.png")
    obraz_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    dolny_zakres = (0, 200, 200)
    gorny_zakres = (10, 255, 255)
    maska = cv2.inRange(obraz_hsv, dolny_zakres, gorny_zakres)
    # Znajdź kontury na podstawie maski
    kontury, _ = cv2.findContours(maska, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Narysuj kontury na oryginalnym obrazie
    wybrany_kontur = kontury[0]

    # Obliczenia i zapisywanie obrazu
    for idx, wybrany_kontur in enumerate(kontury):
        maska_konturu = np.zeros_like(obraz_hsv)
        cv2.drawContours(
            maska_konturu, [wybrany_kontur], 0, (255, 255, 255), thickness=cv2.FILLED
        )
        wyciety_obraz = cv2.bitwise_and(image, maska_konturu)
        x, y, w, h = cv2.boundingRect(wybrany_kontur)
        wyciety_obraz = wyciety_obraz[y : y + h, x : x + w]
        obraz_png = cv2.cvtColor(wyciety_obraz, cv2.COLOR_BGR2BGRA)
        for i in range(obraz_png.shape[0]):
            for j in range(obraz_png.shape[1]):
                if (
                    obraz_png[i, j][0] == 0
                    and obraz_png[i, j][1] == 0
                    and obraz_png[i, j][2] == 0
                ):
                    obraz_png[i, j][3] = 0
        nazwa_wojewodztwa = unidecode(granice_miasta[1])
        folder_path = (
            f"C:/Users/Lenovo Y510p/Documents/Felo/Koszulka/City/{nazwa_wojewodztwa}/"
        )
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)
        global nazwa_miasta
        nazwa_miasta = unidecode(nazwa_miasta)
        nazwa_pliku = f"{nazwa_miasta}.png"
        cv2.imwrite((os.path.join(folder_path, nazwa_pliku)), obraz_png)
        # Clear data
        os.remove("mapa.html")
        os.remove("mapa.png")


tworzenie_obrazu_z_mapy()
maskowanie()
