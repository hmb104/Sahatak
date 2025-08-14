import re
from typing import Dict, Union

def validate_email(email: str) -> bool:
    """
    Validate email format using regex
    
    Args:
        email: Email string to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))

def validate_password(password: str) -> Dict[str, Union[bool, str]]:
    """
    Validate password strength
    
    Args:
        password: Password string to validate
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    if not password or not isinstance(password, str):
        return {
            'valid': False,
            'message': 'Password is required'
        }
    
    # Check minimum length
    if len(password) < 6:
        return {
            'valid': False,
            'message': 'Password must be at least 6 characters long'
        }
    
    # Check maximum length
    if len(password) > 128:
        return {
            'valid': False,
            'message': 'Password must be less than 128 characters long'
        }
    
    # Basic strength check - at least one letter and one number
    has_letter = bool(re.search(r'[a-zA-Z]', password))
    has_number = bool(re.search(r'\d', password))
    
    if not (has_letter and has_number):
        return {
            'valid': False,
            'message': 'Password must contain at least one letter and one number'
        }
    
    return {
        'valid': True,
        'message': 'Password is valid'
    }

def validate_phone(phone: str) -> bool:
    """
    Validate phone number format
    Accepts international format with + or local format
    
    Args:
        phone: Phone number string to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove all spaces and dashes
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone.strip())
    
    # Check for international format (+XXX) or local format
    # Allow 8-15 digits, optionally starting with +
    pattern = r'^\+?[1-9]\d{7,14}$'
    return bool(re.match(pattern, clean_phone))

def validate_full_name(full_name: str, min_length: int = 3, max_length: int = 200) -> Dict[str, Union[bool, str]]:
    """
    Validate full name field (replaces separate first_name/last_name validation)
    
    Args:
        full_name: Full name string to validate
        min_length: Minimum length (default: 3)
        max_length: Maximum length (default: 200)
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    if not full_name or not isinstance(full_name, str):
        return {
            'valid': False,
            'message': 'Full name is required'
        }
    
    full_name = full_name.strip()
    
    if len(full_name) < min_length:
        return {
            'valid': False,
            'message': f'Full name must be at least {min_length} characters long'
        }
    
    if len(full_name) > max_length:
        return {
            'valid': False,
            'message': f'Full name must be less than {max_length} characters long'
        }
    
    # Allow letters, spaces, hyphens, apostrophes, dots, and Arabic characters
    # More permissive for full names which may contain multiple words
    pattern = r"^[a-zA-Z\u0600-\u06FF\s\-'\.]+$"
    if not re.match(pattern, full_name):
        return {
            'valid': False,
            'message': 'Full name contains invalid characters'
        }
    
    # Ensure it contains at least one space (indicating first + last name)
    if ' ' not in full_name:
        return {
            'valid': False,
            'message': 'Please enter your full name (first and last name)'
        }
    
    return {
        'valid': True,
        'message': 'Full name is valid'
    }

def validate_name(name: str, min_length: int = 2, max_length: int = 50) -> Dict[str, Union[bool, str]]:
    """
    Validate individual name field (kept for backwards compatibility)
    For new implementations, use validate_full_name instead
    
    Args:
        name: Name string to validate
        min_length: Minimum length (default: 2)
        max_length: Maximum length (default: 50)
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    if not name or not isinstance(name, str):
        return {
            'valid': False,
            'message': 'Name is required'
        }
    
    name = name.strip()
    
    if len(name) < min_length:
        return {
            'valid': False,
            'message': f'Name must be at least {min_length} characters long'
        }
    
    if len(name) > max_length:
        return {
            'valid': False,
            'message': f'Name must be less than {max_length} characters long'
        }
    
    # Allow letters, spaces, hyphens, apostrophes, and Arabic characters
    pattern = r"^[a-zA-Z\u0600-\u06FF\s\-'\.]+$"
    if not re.match(pattern, name):
        return {
            'valid': False,
            'message': 'Name contains invalid characters'
        }
    
    return {
        'valid': True,
        'message': 'Name is valid'
    }

def validate_age(age: Union[int, str]) -> Dict[str, Union[bool, str]]:
    """
    Validate age
    
    Args:
        age: Age to validate (int or string)
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    try:
        age_int = int(age)
    except (ValueError, TypeError):
        return {
            'valid': False,
            'message': 'Age must be a valid number'
        }
    
    if age_int < 1:
        return {
            'valid': False,
            'message': 'Age must be at least 1'
        }
    
    if age_int > 120:
        return {
            'valid': False,
            'message': 'Age must be less than 120'
        }
    
    return {
        'valid': True,
        'message': 'Age is valid'
    }

def validate_license_number(license_number: str) -> Dict[str, Union[bool, str]]:
    """
    Validate medical license number
    
    Args:
        license_number: License number to validate
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    if not license_number or not isinstance(license_number, str):
        return {
            'valid': False,
            'message': 'License number is required'
        }
    
    license_number = license_number.strip()
    
    if len(license_number) < 3:
        return {
            'valid': False,
            'message': 'License number must be at least 3 characters long'
        }
    
    if len(license_number) > 50:
        return {
            'valid': False,
            'message': 'License number must be less than 50 characters long'
        }
    
    # Allow alphanumeric characters, hyphens, and slashes
    pattern = r'^[a-zA-Z0-9\-\/]+$'
    if not re.match(pattern, license_number):
        return {
            'valid': False,
            'message': 'License number contains invalid characters'
        }
    
    return {
        'valid': True,
        'message': 'License number is valid'
    }

def validate_specialty(specialty: str) -> Dict[str, Union[bool, str]]:
    """
    Validate medical specialty
    
    Args:
        specialty: Medical specialty to validate
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    valid_specialties = [
        'cardiology', 'pediatrics', 'dermatology', 'internal', 
        'psychiatry', 'orthopedics', 'general', 'neurology',
        'gynecology', 'ophthalmology', 'ent', 'surgery',
        'radiology', 'pathology', 'anesthesiology', 'emergency'
    ]
    
    if not specialty or not isinstance(specialty, str):
        return {
            'valid': False,
            'message': 'Specialty is required'
        }
    
    if specialty.lower() not in valid_specialties:
        return {
            'valid': False,
            'message': f'Invalid specialty. Must be one of: {", ".join(valid_specialties)}'
        }
    
    return {
        'valid': True,
        'message': 'Specialty is valid'
    }

def validate_date(date_str: str) -> Dict[str, Union[bool, str]]:
    """
    Validate date string in YYYY-MM-DD format
    
    Args:
        date_str: Date string to validate
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    if not date_str or not isinstance(date_str, str):
        return {
            'valid': False,
            'message': 'Date is required'
        }
    
    try:
        from datetime import datetime
        datetime.strptime(date_str, '%Y-%m-%d')
        return {
            'valid': True,
            'message': 'Date is valid'
        }
    except ValueError:
        return {
            'valid': False,
            'message': 'Invalid date format. Use YYYY-MM-DD'
        }

def validate_appointment_type(appointment_type: str) -> Dict[str, Union[bool, str]]:
    """
    Validate appointment type
    
    Args:
        appointment_type: Appointment type to validate
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    valid_types = ['video', 'audio', 'chat']
    
    if not appointment_type or not isinstance(appointment_type, str):
        return {
            'valid': False,
            'message': 'Appointment type is required'
        }
    
    if appointment_type.lower() not in valid_types:
        return {
            'valid': False,
            'message': f'Invalid appointment type. Must be one of: {", ".join(valid_types)}'
        }
    
    return {
        'valid': True,
        'message': 'Appointment type is valid'
    }

def validate_prescription_data(prescription_data: dict) -> Dict[str, Union[bool, str]]:
    """
    Validate prescription data
    
    Args:
        prescription_data: Dictionary containing prescription details
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    required_fields = ['medication_name', 'dosage', 'frequency', 'duration']
    
    # Check for required fields
    for field in required_fields:
        if not prescription_data.get(field):
            return {
                'valid': False,
                'message': f'{field.replace("_", " ").title()} is required'
            }
    
    # Validate medication name
    medication_name = prescription_data.get('medication_name', '').strip()
    if len(medication_name) < 2 or len(medication_name) > 200:
        return {
            'valid': False,
            'message': 'Medication name must be between 2 and 200 characters'
        }
    
    # Validate dosage
    dosage = prescription_data.get('dosage', '').strip()
    if len(dosage) < 1 or len(dosage) > 100:
        return {
            'valid': False,
            'message': 'Dosage must be between 1 and 100 characters'
        }
    
    # Validate frequency
    frequency = prescription_data.get('frequency', '').strip()
    if len(frequency) < 1 or len(frequency) > 100:
        return {
            'valid': False,
            'message': 'Frequency must be between 1 and 100 characters'
        }
    
    # Validate duration
    duration = prescription_data.get('duration', '').strip()
    if len(duration) < 1 or len(duration) > 100:
        return {
            'valid': False,
            'message': 'Duration must be between 1 and 100 characters'
        }
    
    # Validate optional fields if provided
    if 'quantity' in prescription_data and prescription_data['quantity']:
        quantity = prescription_data['quantity'].strip()
        if len(quantity) > 50:
            return {
                'valid': False,
                'message': 'Quantity must be less than 50 characters'
            }
    
    if 'instructions' in prescription_data and prescription_data['instructions']:
        instructions = prescription_data['instructions'].strip()
        if len(instructions) > 1000:
            return {
                'valid': False,
                'message': 'Instructions must be less than 1000 characters'
            }
    
    if 'notes' in prescription_data and prescription_data['notes']:
        notes = prescription_data['notes'].strip()
        if len(notes) > 1000:
            return {
                'valid': False,
                'message': 'Notes must be less than 1000 characters'
            }
    
    # Validate refills if provided
    if 'refills_allowed' in prescription_data:
        try:
            refills = int(prescription_data['refills_allowed'])
            if refills < 0 or refills > 10:
                return {
                    'valid': False,
                    'message': 'Refills allowed must be between 0 and 10'
                }
        except (ValueError, TypeError):
            return {
                'valid': False,
                'message': 'Refills allowed must be a valid number'
            }
    
    return {
        'valid': True,
        'message': 'Prescription data is valid'
    }

def validate_prescription_status(status: str) -> Dict[str, Union[bool, str]]:
    """
    Validate prescription status
    
    Args:
        status: Status to validate
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    valid_statuses = ['active', 'completed', 'cancelled', 'expired']
    
    if not status or not isinstance(status, str):
        return {
            'valid': False,
            'message': 'Status is required'
        }
    
    if status.lower() not in valid_statuses:
        return {
            'valid': False,
            'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
        }
    
    return {
        'valid': True,
        'message': 'Status is valid'
    }

def validate_json_data(data: dict, required_fields: list) -> Dict[str, Union[bool, str]]:
    """
    Validate JSON data contains required fields
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    if not data or not isinstance(data, dict):
        return {
            'valid': False,
            'message': 'Invalid data provided'
        }
    
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
            missing_fields.append(field)
    
    if missing_fields:
        return {
            'valid': False,
            'message': f'Missing required fields: {", ".join(missing_fields)}'
        }
    
    return {
        'valid': True,
        'message': 'Data is valid'
    }

def validate_medical_history_data(medical_data: dict) -> Dict[str, Union[bool, str]]:
    """
    Validate comprehensive medical history data
    
    Args:
        medical_data: Dictionary containing medical history details
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    # Validate smoking status if provided
    if 'smoking_status' in medical_data and medical_data['smoking_status']:
        valid_smoking = ['never', 'former', 'current']
        if medical_data['smoking_status'] not in valid_smoking:
            return {
                'valid': False,
                'message': f'Invalid smoking status. Must be one of: {", ".join(valid_smoking)}'
            }
    
    # Validate alcohol consumption if provided
    if 'alcohol_consumption' in medical_data and medical_data['alcohol_consumption']:
        valid_alcohol = ['none', 'occasional', 'moderate', 'heavy']
        if medical_data['alcohol_consumption'] not in valid_alcohol:
            return {
                'valid': False,
                'message': f'Invalid alcohol consumption. Must be one of: {", ".join(valid_alcohol)}'
            }
    
    # Validate exercise frequency if provided
    if 'exercise_frequency' in medical_data and medical_data['exercise_frequency']:
        valid_exercise = ['none', 'rare', 'weekly', 'daily']
        if medical_data['exercise_frequency'] not in valid_exercise:
            return {
                'valid': False,
                'message': f'Invalid exercise frequency. Must be one of: {", ".join(valid_exercise)}'
            }
    
    # Validate height if provided (in cm)
    if 'height' in medical_data and medical_data['height']:
        try:
            height = float(medical_data['height'])
            if height < 30 or height > 300:  # Reasonable range
                return {
                    'valid': False,
                    'message': 'Height must be between 30 and 300 cm'
                }
        except (ValueError, TypeError):
            return {
                'valid': False,
                'message': 'Height must be a valid number'
            }
    
    # Validate weight if provided (in kg)
    if 'weight' in medical_data and medical_data['weight']:
        try:
            weight = float(medical_data['weight'])
            if weight < 1 or weight > 1000:  # Reasonable range
                return {
                    'valid': False,
                    'message': 'Weight must be between 1 and 1000 kg'
                }
        except (ValueError, TypeError):
            return {
                'valid': False,
                'message': 'Weight must be a valid number'
            }
    
    # Validate text fields length
    text_fields = {
        'medical_history': 2000,
        'allergies': 1000,
        'current_medications': 1000,
        'chronic_conditions': 1000,
        'family_history': 2000,
        'surgical_history': 2000
    }
    
    for field, max_length in text_fields.items():
        if field in medical_data and medical_data[field]:
            if len(str(medical_data[field])) > max_length:
                return {
                    'valid': False,
                    'message': f'{field.replace("_", " ").title()} must be less than {max_length} characters'
                }
    
    return {
        'valid': True,
        'message': 'Medical history data is valid'
    }

def validate_blood_type(blood_type: str) -> Dict[str, Union[bool, str]]:
    """
    Validate blood type
    
    Args:
        blood_type: Blood type to validate
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    valid_blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    
    if not blood_type or not isinstance(blood_type, str):
        return {
            'valid': True,  # Blood type is optional
            'message': 'Blood type is optional'
        }
    
    if blood_type.upper() not in valid_blood_types:
        return {
            'valid': False,
            'message': f'Invalid blood type. Must be one of: {", ".join(valid_blood_types)}'
        }
    
    return {
        'valid': True,
        'message': 'Blood type is valid'
    }

def validate_history_update_type(update_type: str) -> Dict[str, Union[bool, str]]:
    """
    Validate medical history update type
    
    Args:
        update_type: Update type to validate
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    valid_types = ['initial_registration', 'appointment_update', 'patient_self_update', 'doctor_update']
    
    if not update_type or not isinstance(update_type, str):
        return {
            'valid': False,
            'message': 'Update type is required'
        }
    
    if update_type not in valid_types:
        return {
            'valid': False,
            'message': f'Invalid update type. Must be one of: {", ".join(valid_types)}'
        }
    
    return {
        'valid': True,
        'message': 'Update type is valid'
    }

def validate_doctor_participation_data(participation_data: dict) -> Dict[str, Union[bool, str]]:
    """
    Validate doctor participation and fee data
    
    Args:
        participation_data: Dictionary containing participation details
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    # Validate participation type
    if 'participation_type' in participation_data:
        valid_types = ['volunteer', 'paid']
        if participation_data['participation_type'] not in valid_types:
            return {
                'valid': False,
                'message': f'Invalid participation type. Must be one of: {", ".join(valid_types)}'
            }
    
    # Validate consultation fee
    if 'consultation_fee' in participation_data:
        try:
            fee = float(participation_data['consultation_fee'])
            if fee < 0:
                return {
                    'valid': False,
                    'message': 'Consultation fee cannot be negative'
                }
            
            if fee > 10000:  # Reasonable upper limit
                return {
                    'valid': False,
                    'message': 'Consultation fee cannot exceed 10,000'
                }
            
            # If participation type is volunteer, fee must be 0
            if ('participation_type' in participation_data and 
                participation_data['participation_type'] == 'volunteer' and fee > 0):
                return {
                    'valid': False,
                    'message': 'Volunteer doctors cannot charge fees. Fee must be 0 for volunteer participation.'
                }
            
            # If participation type is paid, fee should be > 0
            if ('participation_type' in participation_data and 
                participation_data['participation_type'] == 'paid' and fee == 0):
                return {
                    'valid': False,
                    'message': 'Paid doctors must set a consultation fee greater than 0'
                }
                
        except (ValueError, TypeError):
            return {
                'valid': False,
                'message': 'Consultation fee must be a valid number'
            }
    
    return {
        'valid': True,
        'message': 'Participation data is valid'
    }

def validate_participation_type(participation_type: str) -> Dict[str, Union[bool, str]]:
    """
    Validate doctor participation type
    
    Args:
        participation_type: Participation type to validate
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    valid_types = ['volunteer', 'paid']
    
    if not participation_type or not isinstance(participation_type, str):
        return {
            'valid': False,
            'message': 'Participation type is required'
        }
    
    if participation_type.lower() not in valid_types:
        return {
            'valid': False,
            'message': f'Invalid participation type. Must be one of: {", ".join(valid_types)}'
        }
    
    return {
        'valid': True,
        'message': 'Participation type is valid'
    }

def validate_consultation_fee(fee: Union[str, float, int], participation_type: str = None) -> Dict[str, Union[bool, str]]:
    """
    Validate consultation fee based on participation type
    
    Args:
        fee: Fee to validate
        participation_type: Doctor's participation type for context validation
        
    Returns:
        dict: Contains 'valid' (bool) and 'message' (str)
    """
    try:
        fee_float = float(fee) if fee is not None else 0.0
    except (ValueError, TypeError):
        return {
            'valid': False,
            'message': 'Consultation fee must be a valid number'
        }
    
    if fee_float < 0:
        return {
            'valid': False,
            'message': 'Consultation fee cannot be negative'
        }
    
    if fee_float > 10000:
        return {
            'valid': False,
            'message': 'Consultation fee cannot exceed 10,000'
        }
    
    # Context-specific validation
    if participation_type:
        if participation_type == 'volunteer' and fee_float > 0:
            return {
                'valid': False,
                'message': 'Volunteer doctors cannot charge fees'
            }
        elif participation_type == 'paid' and fee_float == 0:
            return {
                'valid': False,
                'message': 'Paid doctors must set a consultation fee greater than 0'
            }
    
    return {
        'valid': True,
        'message': 'Consultation fee is valid'
    }

def sanitize_input(text: str, max_length: int = None) -> str:
    """
    Sanitize text input by trimming and optionally limiting length
    
    Args:
        text: Text to sanitize
        max_length: Maximum length to truncate to (optional)
        
    Returns:
        str: Sanitized text
    """
    if not text or not isinstance(text, str):
        return ''
    
    # Strip whitespace
    sanitized = text.strip()
    
    # Limit length if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length].strip()
    
    return sanitized