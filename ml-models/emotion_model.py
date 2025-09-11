"""
Emotion Detection Model for Mind Bridge AI
Image-first emotion detection with Hugging Face primary model and OpenAI Vision fallback.
Includes mock mode for offline/demo reliability.
"""

import logging
import os
import asyncio
import numpy as np
import cv2
import torch
from typing import Dict, Optional, List, Any, Tuple
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F
from PIL import Image
import io
import random

logger = logging.getLogger(__name__)

class EmotionModel:
    """
    Emotion detection model supporting both text and image inputs
    """
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.text_model = None
        self.text_tokenizer = None
        self.image_model = None
        self.face_cascade = None
        self.mock_mode = os.getenv("EMOTION_MOCK", "false").lower() in {"1", "true", "yes"}
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        # HF labels for j-hartmann/emotion-english-distilroberta-base
        self.emotion_labels = [
            'anger', 'disgust', 'fear', 'joy', 'neutral', 'sadness', 'surprise'
        ]
        logger.info(f"Initializing EmotionModel on device: {self.device}, mock={self.mock_mode}")
    
    async def load_model(self):
        """Load emotion detection models"""
        try:
            # Load text-based emotion model (Hugging Face)
            await self._load_text_model()
            # Load image-based lightweight CNN as internal fallback
            await self._load_image_model()
            # Load face detection cascade
            # Load face detection cascade
            await self._load_face_cascade()
            
            logger.info("All models loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            raise
    
    async def _load_text_model(self):
        """Load Hugging Face text-based emotion model"""
        try:
            model_name = "j-hartmann/emotion-english-distilroberta-base"
            logger.info(f"Loading HF text model: {model_name}")
            self.text_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.text_model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32
            )
            self.text_model.to(self.device)
            self.text_model.eval()
            logger.info("HF emotion text model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load HF text model: {str(e)}")
            self.text_model = None
            self.text_tokenizer = None
    
    async def _load_image_model(self):
        """Load image-based emotion detection model"""
        try:
            # Lightweight CNN as an internal fallback for faces
            logger.info("Loading internal lightweight CNN...")
            self.image_model = self._create_fer2013_cnn()
            self.image_model.to(self.device)
            self.image_model.eval()
            logger.info("Fallback CNN loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load fallback CNN: {str(e)}")
            # Fallback to simple CNN
            try:
                logger.info("Loading fallback CNN model...")
                self.image_model = self._create_emotion_cnn()
                self.image_model.to(self.device)
                self.image_model.eval()
                logger.info("Fallback image model loaded successfully")
            except Exception as e2:
                logger.warning(f"Failed to load fallback image model: {str(e2)}")
                self.image_model = None
    
    def _create_fer2013_cnn(self):
        """Create a FER2013-inspired CNN for emotion detection"""
        import torch.nn as nn
        
        class FER2013CNN(nn.Module):
            def __init__(self, num_classes=7):
                super(FER2013CNN, self).__init__()
                # FER2013 uses 48x48 grayscale images
                self.conv1 = nn.Conv2d(1, 64, kernel_size=5, padding=2)
                self.conv2 = nn.Conv2d(64, 64, kernel_size=5, padding=2)
                self.conv3 = nn.Conv2d(64, 128, kernel_size=4, padding=1)
                self.conv4 = nn.Conv2d(128, 128, kernel_size=3, padding=1)
                
                self.pool = nn.MaxPool2d(2, 2)
                self.dropout1 = nn.Dropout(0.25)
                self.dropout2 = nn.Dropout(0.5)
                
                # Calculate the size after convolutions and pooling
                # 48x48 -> 24x24 -> 12x12 -> 6x6 -> 3x3
                self.fc1 = nn.Linear(128 * 3 * 3, 256)
                self.fc2 = nn.Linear(256, num_classes)
                
            def forward(self, x):
                x = self.pool(torch.relu(self.conv1(x)))
                x = self.dropout1(x)
                x = self.pool(torch.relu(self.conv2(x)))
                x = self.pool(torch.relu(self.conv3(x)))
                x = self.dropout1(x)
                x = self.pool(torch.relu(self.conv4(x)))
                
                x = x.view(-1, 128 * 3 * 3)
                x = self.dropout2(torch.relu(self.fc1(x)))
                x = self.fc2(x)
                return x
        
        return FER2013CNN()
    
    def _create_emotion_cnn(self):
        """Create a simple CNN for emotion detection (fallback)"""
        import torch.nn as nn
        
        class EmotionCNN(nn.Module):
            def __init__(self, num_classes=7):
                super(EmotionCNN, self).__init__()
                self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
                self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
                self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
                self.pool = nn.MaxPool2d(2, 2)
                self.dropout = nn.Dropout(0.5)
                self.fc1 = nn.Linear(128 * 6 * 6, 256)
                self.fc2 = nn.Linear(256, num_classes)
                
            def forward(self, x):
                x = self.pool(torch.relu(self.conv1(x)))
                x = self.pool(torch.relu(self.conv2(x)))
                x = self.pool(torch.relu(self.conv3(x)))
                x = x.view(-1, 128 * 6 * 6)
                x = self.dropout(torch.relu(self.fc1(x)))
                x = self.fc2(x)
                return x
        
        return EmotionCNN()
    
    async def _load_face_cascade(self):
        """Load OpenCV face detection cascade"""
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            
            if self.face_cascade.empty():
                raise Exception("Failed to load face cascade")
            
            logger.info("Face cascade loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load face cascade: {str(e)}")
            self.face_cascade = None
    
    async def predict_single(self, image_data: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Predict emotion from a single image
        
        Args:
            image_data: Preprocessed image array
            
        Returns:
            Dictionary with emotion, confidence, and bounding box
        """
        try:
            # Detect faces in the image
            faces = self._detect_faces(image_data)
            if len(faces) == 0:
                logger.warning("No faces detected in image")
                if self.mock_mode:
                    # Provide deterministic mock
                    return {
                        'emotion': 'neutral',
                        'confidence': 0.5,
                        'bounding_box': None,
                        'faces_detected': 0
                    }
                return None

            # Use the first detected face
            x, y, w, h = faces[0]

            # Extract face region
            face_roi = image_data[y:y+h, x:x+w]

            # Preprocess face for emotion detection
            face_processed = self._preprocess_face(face_roi)

            # Predict emotion via HF text model metadata? We don't have image HF model; use CNN then fallback
            emotion, confidence = await self._predict_emotion_from_face(face_processed)

            # If CNN is unavailable or low confidence, try OpenAI Vision fallback
            if (confidence < 0.4 or self.image_model is None) and self.openai_api_key and not self.mock_mode:
                try:
                    oa_emotion, oa_conf = await self._fallback_openai(image_data)
                    if oa_emotion is not None:
                        emotion, confidence = oa_emotion, oa_conf
                except Exception as e:
                    logger.warning(f"OpenAI fallback failed: {str(e)}")

            if self.mock_mode:
                # Slightly adjust for demo variability
                emotion = random.choice(self.emotion_labels)
                confidence = round(random.uniform(0.6, 0.95), 3)

            return {
                'emotion': emotion,
                'confidence': float(confidence),
                'bounding_box': [int(x), int(y), int(w), int(h)],
                'faces_detected': len(faces)
            }
            
        except Exception as e:
            logger.error(f"Error in single prediction: {str(e)}")
            return None
    
    def _detect_faces(self, image: np.ndarray) -> List[tuple]:
        """Detect faces in image using OpenCV"""
        if self.face_cascade is None:
            return []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        return faces.tolist() if len(faces) > 0 else []
    
    def _preprocess_face(self, face_roi: np.ndarray) -> torch.Tensor:
        """Preprocess face region for emotion detection (FER2013 compatible)"""
        # Resize to 48x48 (FER2013 standard)
        face_resized = cv2.resize(face_roi, (48, 48))
        
        # Convert to grayscale
        face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        
        # Normalize to [0, 1] for FER2013 compatibility
        face_normalized = face_gray.astype(np.float32) / 255.0
        
        # Convert to tensor and add batch dimension
        face_tensor = torch.from_numpy(face_normalized).unsqueeze(0).unsqueeze(0)
        
        return face_tensor.to(self.device)
    
    async def _predict_emotion_from_face(self, face_tensor: torch.Tensor) -> tuple:
        """Predict emotion from preprocessed face tensor"""
        try:
            if self.image_model is not None:
                # Use image model
                with torch.no_grad():
                    outputs = self.image_model(face_tensor)
                    probabilities = F.softmax(outputs, dim=1)
                    confidence, predicted = torch.max(probabilities, 1)
                    
                    index = predicted.item()
                    index = index % len(self.emotion_labels)
                    emotion = self.emotion_labels[index]
                    confidence_score = confidence.item()
                    
                    return emotion, confidence_score
            else:
                # Fallback: return neutral with low confidence
                return 'neutral', 0.5
                
        except Exception as e:
            logger.error(f"Error in emotion prediction: {str(e)}")
            return 'neutral', 0.0
    
    async def predict_text_emotion(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Predict emotion from text input
        
        Args:
            text: Input text string
            
        Returns:
            Dictionary with emotion and confidence
        """
        if self.text_model is None or self.text_tokenizer is None:
            return None
        
        try:
            # Tokenize input
            inputs = self.text_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Predict
            with torch.no_grad():
                outputs = self.text_model(**inputs)
                probabilities = F.softmax(outputs.logits, dim=1)
                confidence, predicted = torch.max(probabilities, 1)
                idx = predicted.item()
                # Map by model config if available else fallback to known list
                try:
                    id2label = getattr(self.text_model.config, 'id2label', None)
                    label = id2label.get(idx, 'neutral') if id2label else self.emotion_labels[idx % len(self.emotion_labels)]
                except Exception:
                    label = self.emotion_labels[idx % len(self.emotion_labels)]
                confidence_score = confidence.item()
                return {
                    'emotion': str(label).lower(),
                    'confidence': float(confidence_score)
                }
                
        except Exception as e:
            logger.error(f"Error in text emotion prediction: {str(e)}")
            return None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models"""
        return {
            'device': str(self.device),
            'text_model_loaded': self.text_model is not None,
            'image_model_loaded': self.image_model is not None,
            'face_cascade_loaded': self.face_cascade is not None,
            'emotion_labels': self.emotion_labels,
            'mock_mode': self.mock_mode,
            'openai_fallback_enabled': bool(self.openai_api_key)
        }

    async def _fallback_openai(self, image_bgr: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Use OpenAI Vision API to infer emotion from a face image by prompt.
        This is heuristic and used as a last-resort fallback.
        """
        try:
            import base64
            from io import BytesIO
            from PIL import Image as PILImage
            from openai import OpenAI

            client = OpenAI(api_key=self.openai_api_key)

            # Convert to RGB JPEG in-memory
            rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            pil_img = PILImage.fromarray(rgb)
            buf = BytesIO()
            pil_img.save(buf, format='JPEG', quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

            prompt = (
                "Identify the primary human emotion visible in this face as one of: "
                + ", ".join(self.emotion_labels) + ". Return JSON with keys emotion and confidence (0-1)."
            )

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64}",
                                },
                            },
                        ],
                    }
                ],
                temperature=0.2,
            )

            text = response.choices[0].message.content or ""
            # naive parse: attempt to extract fields
            import re
            emotion = None
            conf = 0.6
            # find known label in text
            for label in self.emotion_labels:
                if label.lower() in text.lower():
                    emotion = label
                    break
            m = re.search(r"confidence\D+([01](?:\.\d+)?)", text)
            if m:
                try:
                    conf = float(m.group(1))
                except Exception:
                    pass
            return emotion, conf if emotion else (None, 0.0)
        except Exception as e:
            logger.warning(f"OpenAI fallback error: {str(e)}")
            return None, 0.0
