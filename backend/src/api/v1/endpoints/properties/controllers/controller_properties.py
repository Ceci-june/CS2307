import os
from starlette import status


from src.api.base.controller import BaseController
from src.api.v1.endpoints.properties.repositories.repo_properties import (
    repo_get_properties,
    repo_add_log,
)
from src.settings.event import recommendation_service, llm_model
from src.services.llm.const.prompt import get_system_prompt, get_user_prompt
from src.utils.functions import parse_json_llm_response


class PropertiesController(BaseController):
    async def ctr_get_properties(
        self,
        query: str,
        min_price: float,
        max_price: float,
        min_area: float,
        max_area: float,
        bedrooms: int,
        bathrooms: int,
        legal_status: str,
        furniture: str,
        house_direction: str,
        balcony_direction: str,
        min_frontage: float,
        min_road_width: float,
        sort_by: str,
        sort_order: str,
        page: int,
        limit: int,
        property_type: str,
        district: str = None,
        pool: bool = None,
        gym: bool = None,
        park: bool = None,
        bbq: bool = None,
        kids_playground: bool = None,
        sports_court: bool = None,
        security_24h: bool = None,
        reception: bool = None,
        elevator: bool = None,
        parking: bool = None,
        near_metro: bool = None,
        near_bus: bool = None,
        near_highway: bool = None,
        near_school: bool = None,
        near_hospital: bool = None,
        near_mall: bool = None,
        near_market: bool = None,
        near_park: bool = None,
        river_view: bool = None,
        park_view: bool = None,
        city_view: bool = None,
        balcony: bool = None,
        garden: bool = None,
        garage: bool = None,
        terrace: bool = None,
    ):
        """
        Controller to get list of properties for listing page.
        Currently returns dummy data from repository layer.
        """
        try:
            if page < 1 and limit < 1:
                self.errors.append(
                    {
                        "loc": "PropertiesController -> ctr_get_properties",
                        "msg": "Page and limit must be greater than 0",
                        "detail": "Page and limit must be greater than 0",
                    }
                )
                return self.response(data=None, status_code=status.HTTP_400_BAD_REQUEST)
            
            is_success, data, error = repo_get_properties(
                query=query,
                min_price=min_price,
                max_price=max_price,
                min_area=min_area,
                max_area=max_area,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                legal_status=legal_status,
                furniture=furniture,
                house_direction=house_direction,
                balcony_direction=balcony_direction,
                min_frontage=min_frontage,
                min_road_width=min_road_width,
                sort_by=sort_by,
                sort_order=sort_order,
                page=page,
                limit=limit,
                property_type=property_type,
                district=district,
                pool=pool,
                gym=gym,
                park=park,
                bbq=bbq,
                kids_playground=kids_playground,
                sports_court=sports_court,
                security_24h=security_24h,
                reception=reception,
                elevator=elevator,
                parking=parking,
                near_metro=near_metro,
                near_bus=near_bus,
                near_highway=near_highway,
                near_school=near_school,
                near_hospital=near_hospital,
                near_mall=near_mall,
                near_market=near_market,
                near_park=near_park,
                river_view=river_view,
                park_view=park_view,
                city_view=city_view,
                balcony=balcony,
                garden=garden,
                garage=garage,
                terrace=terrace,
            )
            if not is_success:
                self.errors.append(
                    {
                        "loc": "PropertiesController -> ctr_get_properties",
                        "msg": error,
                        "detail": error,
                    }
                )
                return self.response(
                    data=None, status_code=status.HTTP_400_BAD_REQUEST
                )

            return self.response(data=data, status_code=status.HTTP_200_OK)
        except Exception as e:
            self.errors.append(
                {
                    "loc": "PropertiesController -> ctr_get_properties",
                    "msg": "Internal server error",
                    "detail": str(e),
                }
            )
            return self.response(
                data=None, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def ctr_ai_search(
        self,
        question: str,
        min_price: float,
        max_price: float,
        min_area: float,
        max_area: float,
        bedrooms: int,
        bathrooms: int,
        legal_status: str,
        furniture: str,
        house_direction: str,
        balcony_direction: str,
        length_road_entrance: float,
        district: str = None,
        pool: bool = None,
        gym: bool = None,
        park: bool = None,
        bbq: bool = None,
        kids_playground: bool = None,
        sports_court: bool = None,
        security_24h: bool = None,
        reception: bool = None,
        elevator: bool = None,
        parking: bool = None,
        near_metro: bool = None,
        near_bus: bool = None,
        near_highway: bool = None,
        near_school: bool = None,
        near_hospital: bool = None,
        near_mall: bool = None,
        near_market: bool = None,
        near_park: bool = None,
        river_view: bool = None,
        park_view: bool = None,
        city_view: bool = None,
        balcony: bool = None,
        garden: bool = None,
        garage: bool = None,
        terrace: bool = None,
    ):
        """
        Controller to get AI search.
        """
        try:
            is_success, data_response, error = await recommendation_service.ai_recommendation(
                question=question,
                min_price=min_price,
                max_price=max_price,
                min_area=min_area,
                max_area=max_area,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                legal_status=legal_status,
                furniture=furniture,
                house_direction=house_direction,
                balcony_direction=balcony_direction,
                length_road_entrance=length_road_entrance,
                district=district,
                pool=pool,
                gym=gym,
                park=park,
                bbq=bbq,
                kids_playground=kids_playground,
                sports_court=sports_court,
                security_24h=security_24h,
                reception=reception,
                elevator=elevator,
                parking=parking,
                near_metro=near_metro,
                near_bus=near_bus,
                near_highway=near_highway,
                near_school=near_school,
                near_hospital=near_hospital,
                near_mall=near_mall,
                near_market=near_market,
                near_park=near_park,
                river_view=river_view,
                park_view=park_view,
                city_view=city_view,
                balcony=balcony,
                garden=garden,
                garage=garage,
                terrace=terrace,
            )
            
            if not data_response:
                self.errors.append(
                    {
                        "loc": "PropertiesController -> ctr_ai_search",
                        "msg": "Không tìm thấy căn hộ phù hợp",
                        "detail": "Không tìm thấy căn hộ phù hợp",
                    }
                )
                return self.response(data=None, status_code=status.HTTP_400_BAD_REQUEST)
            
            user_request = f"""
            Giá tối thiểu: {min_price}
            Giá tối đa: {max_price}
            Diện tích tối thiểu: {min_area}
            Diện tích tối đa: {max_area}
            Số phòng ngủ: {bedrooms}
            Số phòng tắm: {bathrooms}
            Trạng thái pháp lý: {legal_status}
            Tiện ích: {furniture}
            Hướng nhà: {house_direction}
            Hướng ban công: {balcony_direction}
            Độ dài đường vào căn hộ: {length_road_entrance}
            Quận: {district}
            Có hồ bơi: {pool}
            Có gym: {gym}
            Có công viên: {park}
            Có BBQ: {bbq}
            Có playground cho trẻ em: {kids_playground}
            Có sân thể thao: {sports_court}
            Có bảo vệ 24/7: {security_24h}
            Có reception: {reception}
            Có thang máy: {elevator}
            Có parking: {parking}
            Gần metro: {near_metro}
            Gần bus: {near_bus}
            Gần đường cao tốc: {near_highway}
            Gần trường học: {near_school}
            Gần bệnh viện: {near_hospital}
            Gần mall: {near_mall}
            Gần chợ: {near_market}
            Gần công viên: {near_park}
            Có view sông: {river_view}
            Có view công viên: {park_view}
            Có view thành phố: {city_view}
            Có ban công: {balcony}
            Có sân vườn: {garden}
            Có gara: {garage}
            Có sân thể thao: {sports_court}
            """
            
            is_success, data_llm, error = await llm_model.ask_llm(
                system_prompt=get_system_prompt(),
                user_prompt=get_user_prompt(user_request, data_response),
            )
            
            repo_add_log(
                user_id=None,
                action="ai_search",
                content="Lấy kết quả từ AI",
                metadata={
                    "data_response": data_response, 
                    "data_llm": data_llm,
                    "user_request": user_request,
                    "error": error,
                },
            )
            if not is_success:
                self.errors.append(
                    {
                        "loc": "PropertiesController -> ctr_ai_search",
                        "msg": error,
                        "detail": error,
                    }
                )
                return self.response(data=None, status_code=status.HTTP_400_BAD_REQUEST)
            data_llm = parse_json_llm_response(data_llm)
            
            data_res = []
            for index, item in enumerate(data_response):
                if index < len(data_llm):
                    item["explanation"] = data_llm[index]["explanation"]
                    item["comparison"] = data_llm[index]["comparison"]
                data_res.append(item)
            return self.response(data=data_res, status_code=status.HTTP_200_OK)
        except Exception as e:
            self.errors.append(
                {
                    "loc": "PropertiesController -> ctr_ai_search",
                    "msg": "Internal server error",
                    "detail": str(e),
                }
            )
            return self.response(data=None, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)