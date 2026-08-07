import pandas as pd

class Outside_Port(zone, Enum):
    def __init__:
        self.zone = zone
        
    def get_prices():
        callresult= print("Placeholder for a json file from saved files of elspotprices").filter(priceArea == self.zone)
        price_data = pd.DataFrame()
        price_data['HourUTC']=callresult['HourUTC']
        price_data['SpotPriceEUR']=callresult['SpotPriceEUR']
        return price_data
   
    
    
    def get_wind_generation():
        
        callresult= print("Placeholder for a json file from saved files of DeclarationProduction").filter(priceArea== self.zone)
        wind_data = pd.DataFrame()
        wind_data['HourUTC']= callresult['HourUTC']
        wind_data['WindProd_MWh']=callresult['Production_MWh']
        return wind_data