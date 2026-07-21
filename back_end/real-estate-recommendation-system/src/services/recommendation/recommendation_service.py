import numpy as np
import pickle
from datetime import date, datetime
from sklearn.metrics.pairwise import cosine_similarity
import torch
from transformers import AutoTokenizer, AutoModelForMaskedLM
from src.services.inference.recommender import passes_hard_filters, infer_profile, score_property

tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base")
model = AutoModelForMaskedLM.from_pretrained("vinai/phobert-base")

class RecommendationService:
    def __init__(self):
        pass

    def start(self):
        pass
    
    def _embed_text(self, text: str) -> np.ndarray:
        try:
            inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
            with torch.no_grad():
                outputs = model(**inputs, output_hidden_states=True)
            embeddings = outputs.hidden_states[-1]
            mask = inputs['attention_mask']
            mask_expanded = mask.unsqueeze(-1).expand(embeddings.size()).float()
            sum_embeddings = (embeddings * mask_expanded).sum(1)
            sum_mask = mask_expanded.sum(1)
            embedding = sum_embeddings / sum_mask.clamp(min=1e-9)
            return embedding.numpy()[0]
        except Exception as e:
            print(f"Error embedding text: {e}")
            return np.zeros(768)

    def _prepare_request_text(self, request: dict) -> str:
        """
        Chuẩn bị text từ request để embedding
        """
        parts = []
        
        if "question" in request and request["question"]:
            parts.append(str(request["question"]))
        
        if "min_price" in request and request["min_price"]:
            parts.append(f"Giá tối thiểu {request['min_price']} tỷ")
        
        if "max_price" in request and request["max_price"]:
            parts.append(f"Giá tối đa {request['max_price']} tỷ")
        
        if "min_area" in request and request["min_area"]:
            parts.append(f"Diện tích tối thiểu {request['min_area']} m2")
        
        if "max_area" in request and request["max_area"]:
            parts.append(f"Diện tích tối đa {request['max_area']} m2")
        
        if "bedrooms" in request and request["bedrooms"]:
            parts.append(f"Số phòng ngủ {request['bedrooms']}")
        
        if "bathrooms" in request and request["bathrooms"]:
            parts.append(f"Số phòng tắm {request['bathrooms']}")
        
        if "legal_status" in request and request["legal_status"]:
            parts.append(f"Pháp lý {request['legal_status']}")
        
        if "furniture" in request and request["furniture"]:
            parts.append(f"Nội thất {request['furniture']}")
        
        if "house_direction" in request and request["house_direction"]:
            parts.append(f"Hướng nhà {request['house_direction']}")
        
        if "balcony_direction" in request and request["balcony_direction"]:
            parts.append(f"Hướng ban công {request['balcony_direction']}")
        
        if "length_road_entrance" in request and request["length_road_entrance"]:
            parts.append(f"Độ dài mặt tiền {request['length_road_entrance']} mét")
        if "district" in request and request["district"]:
            parts.append(f"Quận {request['district']}")
            
        return " ".join(parts) if parts else "property search"

    async def ai_recommendation(
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
        try:
            select_columns = """
                id,
                listing_id,
                listing_type,
                posted_date,
                expiry_date,
                property_type,
                city_province,
                district,
                images,
                folder,
                title,
                address,
                old_address,
                location_link,
                latitude_longitude,
                description,
                area_price_history,
                price_range,
                area,
                bedrooms,
                bathrooms,
                legal_status,
                furnishing,
                balcony_direction,
                house_direction,
                pool,
                gym,
                park,
                bbq,
                kids_playground,
                sports_court,
                security_24h,
                reception,
                elevator,
                parking,
                near_metro,
                near_bus,
                near_highway,
                near_school,
                near_hospital,
                near_mall,
                near_market,
                near_park,
                river_view,
                park_view,
                city_view,
                balcony,
                garden,
                garage,
                terrace,
                frontage,
                access_road,
                metadata,
                is_active,
                is_deleted,
                updated_at,
                created_at
            """.strip()
            request = {
                "question": question,
                "min_price": min_price,
                "max_price": max_price,
                "min_area": min_area,
                "max_area": max_area,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "legal_status": legal_status,
                "furniture": furniture,
                "house_direction": house_direction,
                "balcony_direction": balcony_direction,
                "length_road_entrance": length_road_entrance,
                "district": district,
                "pool": pool,
                "gym": gym,
                "park": park,
                "bbq": bbq,
                "kids_playground": kids_playground,
                "sports_court": sports_court,
                "security_24h": security_24h,
                "reception": reception,
                "elevator": elevator,
                "parking": parking,
                "near_metro": near_metro,
                "near_bus": near_bus,
                "near_highway": near_highway,
                "near_school": near_school,
                "near_hospital": near_hospital,
                "near_mall": near_mall,
                "near_market": near_market,
                "near_park": near_park,
                "river_view": river_view,
                "park_view": park_view,
                "city_view": city_view,
                "balcony": balcony,
                "garden": garden,
                "garage": garage,
                "terrace": terrace,
            }
            from src.settings.event import postgres_client
            properties = postgres_client.execute_raw_query(
                f"""
                SELECT {select_columns}
                FROM properties
                WHERE is_deleted = false AND is_active = true
                ORDER BY created_at DESC
                """
            ) or []
            column_names = [column.strip()for column in select_columns.split(",")]
            payloads = [dict(zip(column_names, row)) for row in properties]
            
            for payload in payloads:
                for key, value in list(payload.items()):
                    if isinstance(value, (datetime, date)):
                        payload[key] = value.isoformat()

            profile = infer_profile(request)
            hard_filter_candidates = [payload for payload in payloads if passes_hard_filters(payload, request)]
            
            candidates = list(hard_filter_candidates)
            if not candidates:
                candidates = payloads
                profile["fallback_mode"] = "score_all_properties"
                
            scored = [score_property(payload, request, profile) for payload in candidates]
            
            # Embedding re-ranking
            with open('./src/data/embeddings.pkl', 'rb') as f:
                embeddings_df = pickle.load(f)
            embeddings_df = embeddings_df.set_index('listing_id')
            print("Shape of feature_matrix:", embeddings_df.shape)
            
            request_question = request.get("question", "").strip()
            
            if len(scored) > 0 and request_question != "":
                try:
                    request_text = self._prepare_request_text(request)
                    print(request_text)
                    request_embedding = self._embed_text(request_text)
                    for item in scored:
                        
                        item_id = item["listing_id"]
                        if item_id in embeddings_df.index:
                            property_embedding = embeddings_df.loc[item_id].values
                            if property_embedding.shape != (768,):
                                property_embedding = property_embedding[0]
                                
                            similarity_score = cosine_similarity(
                                request_embedding.reshape(1, -1),
                                property_embedding.reshape(1, -1)
                            )[0][0]
                        else:
                            similarity_score = 0.0 

                        item['combined_score'] = item['overall_score'] + similarity_score
                    
                    # Xếp hạng theo điểm kết hợp
                    ranked = sorted(scored, key=lambda x: x.get('combined_score', x['overall_score']), reverse=True)
                    top_results = ranked[:3]
                    
                except Exception as embedding_error:
                    print(f"Error in embedding combined score: {embedding_error}")
                    ranked = sorted(scored, key=lambda x: x['overall_score'], reverse=True)
                    top_results = ranked[:3]
            else:
                ranked = sorted(scored, key=lambda x: x['overall_score'], reverse=True)
                top_results = ranked[:3]
            
            data_res = [item['property_payload'] for item in top_results]
            return True, data_res, None
            
        except Exception as e:
            import traceback
            traceback.print_exc() 
            return False, None, str(e)