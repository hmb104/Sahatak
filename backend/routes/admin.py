from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from models import db, User, Patient, Doctor, Appointment
from datetime import datetime, timedelta
from routes.notifications import queue_notification, send_email
from sqlalchemy import func, text, and_, or_
from sqlalchemy.orm import joinedload

# utils import
from utils.responses import APIResponse
from utils.responses import APIResponse, ErrorCodes
from utils.error_handlers import RequestValidationError
from utils.validators import validate_name, validate_phone, validate_age
from utils.logging_config import app_logger, log_user_action
from utils.logging_config import auth_logger, log_user_action
from utils.validators import validate_email, validate_password

# Database import
from models import SystemSettings
from models import AuditLog

# Create admin blueprint
admin_bp = Blueprint('admin', __name__)

# Admin Authentication Decorator
def admin_required(f):
    """
    Decorator to check if user is admin with proper permissions
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return APIResponse.error(
                message="Authentication required",
                status_code=401,
                error_code="AUTH_REQUIRED"
            )
        
        # Check if user has admin role
        if not hasattr(current_user, 'user_type') or current_user.user_type != 'admin':
            log_user_action(
                current_user.id if current_user.is_authenticated else None,
                'admin_access_denied',
                {'endpoint': request.endpoint, 'ip': request.remote_addr}
            )
            return APIResponse.error(
                message="Admin access required",
                status_code=403,
                error_code="ADMIN_REQUIRED"
            )
        
        return f(*args, **kwargs)
    return decorated_function

# Input validation helpers
def validate_pagination_params(page=1, per_page=20):
    """Validate and sanitize pagination parameters"""
    try:
        page = max(1, int(page))
        per_page = min(100, max(1, int(per_page)))  # Cap at 100 items per page
        return page, per_page
    except ValueError:
        raise RequestValidationError("Invalid pagination parameters")

def validate_date_range(start_date, end_date):
    """Validate date range parameters"""
    try:
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        if start_date and end_date and start_date > end_date:
            raise RequestValidationError("Start date must be before end date")
            
        return start_date, end_date
    except ValueError:
        raise RequestValidationError("Invalid date format")

# =============================================================================
# USER MANAGEMENT ENDPOINTS
# =============================================================================

@admin_bp.route('/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    """Get paginated list of users with filtering and search"""
    try:
        # Placeholder implementation
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        user_type = request.args.get('user_type')
        search = request.args.get('search')
        status = request.args.get('status')
        
        page, per_page = validate_pagination_params(page, per_page)
        
        # Build base query
        query = User.query.options(
            joinedload(User.patient),
            joinedload(User.doctor)
        )
        
        # Apply filters
        if user_type and user_type in ['patient', 'doctor', 'admin']:
            query = query.filter(User.user_type == user_type)
        
        if status is not None:
            is_active = status.lower() == 'true'
            query = query.filter(User.is_active == is_active)
        
        if search:
            search_filter = or_(
                User.full_name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        # Apply pagination
        users_pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Format user data (exclude sensitive information)
        users_data = []
        for user in users_pagination.items:
            user_info = {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'phone': user.phone,
                'user_type': user.user_type,
                'is_active': user.is_active,
                'is_verified': user.is_verified,
                'created_at': user.created_at.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'profile_completed': user.profile_completed
            }
            
            # Add type-specific information
            if user.user_type == 'doctor' and user.doctor:
                user_info['doctor_info'] = {
                    'specialty': user.doctor.specialty,
                    'license_number': user.doctor.license_number,
                    'is_verified': user.doctor.is_verified,
                    'years_of_experience': user.doctor.years_of_experience
                }
            elif user.user_type == 'patient' and user.patient:
                user_info['patient_info'] = {
                    'date_of_birth': user.patient.date_of_birth.isoformat() if user.patient.date_of_birth else None,
                    'gender': user.patient.gender,
                    'emergency_contact': user.patient.emergency_contact
                }
            
            users_data.append(user_info)
        
        # Log admin action
        log_user_action(
            current_user.id,
            'admin_view_users',
            {
                'page': page,
                'per_page': per_page,
                'filters': {
                    'user_type': user_type,
                    'search': bool(search),
                    'status': status
                },
                'total_results': users_pagination.total
            }
        )
        
        return APIResponse.success(
            data={
                'users': users_data,
                'pagination': {
                    'page': users_pagination.page,
                    'pages': users_pagination.pages,
                    'per_page': users_pagination.per_page,
                    'total': users_pagination.total,
                    'has_next': users_pagination.has_next,
                    'has_prev': users_pagination.has_prev
                }
            },
            message="Users retrieved successfully"
        )
        
    except RequestValidationError as e:
        return APIResponse.error(message=str(e), status_code=400)
    except Exception as e:
        app_logger.error(f"Admin get users error: {str(e)}")
        return APIResponse.error(
            message="Failed to retrieve users",
            status_code=500
        )

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_user_details(user_id):
    """Get user details for admin view"""
    try:
        user = User.query.options(
            joinedload(User.patient),
            joinedload(User.doctor)
        ).get(user_id)
        
        if not user:
            return APIResponse.error(
                message="User not found",
                status_code=404,
                error_code="USER_NOT_FOUND"
            )
        
        # Format comprehensive user data (exclude medical records) 
        user_data = {
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'phone': user.phone,
            'user_type': user.user_type,
            'is_active': user.is_active,
            'is_verified': user.is_verified,
            'created_at': user.created_at.isoformat(),
            'updated_at': user.updated_at.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'locked_until': user.locked_until.isoformat() if user.locked_until else None
        }
          # Add type-specific detailed information
        if user.user_type == 'doctor' and user.doctor:
            user_data['doctor_details'] = {
                'specialty': user.doctor.specialty,
                'license_number': user.doctor.license_number,
                'years_of_experience': user.doctor.years_of_experience,
                'bio': user.doctor.bio,
                'consultation_fee': float(user.doctor.consultation_fee) if user.doctor.consultation_fee else None,
                'is_verified': user.doctor.is_verified,
                'verification_date': user.doctor.verification_date.isoformat() if user.doctor.verification_date else None,
                'verification_notes': user.doctor.verification_notes,
                'rating': float(user.doctor.rating) if user.doctor.rating else None,
                'total_consultations': user.doctor.total_consultations,
                'available_days': user.doctor.available_days,
                'available_time_start': user.doctor.available_time_start.isoformat() if user.doctor.available_time_start else None,
                'available_time_end': user.doctor.available_time_end.isoformat() if user.doctor.available_time_end else None
            }
        elif user.user_type == 'patient' and user.patient:
            user_data['patient_details'] = {
                'date_of_birth': user.patient.date_of_birth.isoformat() if user.patient.date_of_birth else None,
                'gender': user.patient.gender,
                'blood_type': user.patient.blood_type,
                'height_cm': user.patient.height_cm,
                'weight_kg': user.patient.weight_kg,
                'emergency_contact': user.patient.emergency_contact,
                'emergency_phone': user.patient.emergency_phone,
                'address': user.patient.address,
                'city': user.patient.city,
                'total_appointments': user.patient.total_appointments
            }
        
        # Get recent activity (last 10 appointments)
        recent_appointments = Appointment.query.filter_by(
            patient_id=user_id if user.user_type == 'patient' else None,
            doctor_id=user_id if user.user_type == 'doctor' else None
        ).order_by(Appointment.created_at.desc()).limit(10).all()
        
        user_data['recent_activity'] = [{
            'id': apt.id,
            'date': apt.appointment_date.isoformat(),
            'status': apt.status,
            'type': 'appointment',
            'with_user': apt.doctor.user.full_name if user.user_type == 'patient' else apt.patient.user.full_name
        } for apt in recent_appointments]
        
        log_user_action(
            current_user.id,
            'admin_view_user_details',
            {'target_user_id': user_id, 'user_type': user.user_type}
        )
        return APIResponse.success(
            data={'user': user_data},
            message="User details retrieved"
        )
        
    except Exception as e:
        app_logger.error(f"Admin get user details error: {str(e)}")
        return APIResponse.error(
            message="Failed to retrieve user details",
            status_code=500
        )

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Ahmed: Toggle user active status"""
    try:
        user = User.query.get_or_404(user_id)
        
        if not user:
            return APIResponse.error(
                message="User not found",
                status_code=404,
                error_code="USER_NOT_FOUND"
            )
        
        # Prevent admin from deactivating themselves
        if user_id == current_user.id:
            return APIResponse.error(
                message="Cannot change your own status",
                status_code=400,
                error_code="CANNOT_MODIFY_SELF"
            )
        
        old_status = user.is_active
        user.is_active = not user.is_active
        user.updated_at = datetime.utcnow()
        db.session.commit()
            
        # Send notification to user
        notification_title = "Account Status Update"
        notification_message = f"Your account has been {'activated' if user.is_active else 'deactivated'} by an administrator."
              
        queue_notification(
            user_id=user_id,
            title=notification_title,
            message=notification_message,
            notification_type='warning' if not user.is_active else 'info',
            send_email=True,
            send_sms=False
        )
        
        # Log admin action
        log_user_action(
            current_user.id,
            'admin_toggle_user_status',
            {
                'target_user_id': user_id,
                'target_email': user.email, # i add the email
                'old_status': old_status,
                'new_status': user.is_active
            }
        )
        
        return APIResponse.success(
            data={'user_id': user_id, 'is_active': user.is_active},
            message=f"User {'activated' if user.is_active else 'deactivated'} successfully"
        )
        
    except Exception as e:
        app_logger.error(f"Admin toggle user status error: {str(e)}")
        return APIResponse.error(
            message="Failed to update user status",
            status_code=500
        )

# =============================================================================
# DOCTOR VERIFICATION ENDPOINTS
# =============================================================================
# Get list of doctors pending verification
@admin_bp.route('/doctors/pending-verification', methods=['GET'])
@login_required
@admin_required
def get_pending_verifications():
    try:
        pending_doctors = Doctor.query.filter_by(is_verified=False).all()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        page, per_page = validate_pagination_params(page, per_page)
        
        # Query unverified doctors with user details
        pending_query = Doctor.query.options(
            joinedload(Doctor.user)
        ).filter(
            and_(
                Doctor.is_verified == False,
                User.is_active == True
            )
        ).join(User).order_by(Doctor.created_at.asc())
        
        pending_pagination = pending_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Format doctor data for verification
        doctors_data = []
        for doctor in pending_pagination.items:
            doctors_info = {
                'id': doctor.id,
                'user_id': doctor.user_id,
                'name': doctor.user.full_name,
                'email': doctor.user.email,
                'phone': doctor.user.phone,
                'specialty': doctor.specialty,
                'license_number': doctor.license_number,
                'bio': doctor.bio,
                'years_of_experience': doctor.years_of_experience,
                'submitted_at': doctor.created_at.isoformat(),
                'days_waiting': (datetime.utcnow() - doctor.created_at).days,
                'documents_submitted': {
                    'license_document': bool(doctor.license_document_path),
                    'cv_document': bool(doctor.cv_document_path),
                    'profile_photo': bool(doctor.profile_photo_path)
                }
            }
            doctors_data.append(doctors_info)
        
        log_user_action(
            current_user.id,
            'admin_view_pending_verifications',
            {'page': page, 'total_pending': pending_pagination.total}
        )
        
        return APIResponse.success(
            data={
                'pending_doctors': doctors_data,
                'pagination': {
                    'page': pending_pagination.page,
                    'pages': pending_pagination.pages,
                    'per_page': pending_pagination.per_page,
                    'total': pending_pagination.total,
                    'has_next': pending_pagination.has_next,
                    'has_prev': pending_pagination.has_prev
                }
            },
            message="Pending verifications retrieved"
        )
        
    except Exception as e:
        app_logger.error(f"Admin get pending verifications error: {str(e)}")
        return APIResponse.error(
            message="Failed to retrieve pending verifications",
            status_code=500
        )
#Verify a doctor
@admin_bp.route('/doctors/<int:doctor_id>/verify', methods=['POST'])
@login_required
@admin_required
def verify_doctor(doctor_id):    
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error(
                message="Request body required",
                status_code=400
            )
            
        approved = data.get('approved', False)
        notes = data.get('notes', '').strip()
        
        doctor = Doctor.query.options(joinedload(Doctor.user)).get(doctor_id)
        if not doctor:
            return APIResponse.error(
                message="Doctor not found",
                status_code=404,
                error_code="DOCTOR_NOT_FOUND"
            )
      
       # Verification notes field 
        if approved:
            doctor.is_verified = True
            doctor.verification_date = datetime.utcnow()
            doctor.verification_notes = notes
            doctor.verified_by = current_user.id
            
             # Send approval email
            email_subject = "Doctor Verification Approved - Sahatak Platform"
            email_body = f"""
            Dear Dr. {doctor.user.full_name},

            Congratulations! Your doctor profile has been verified and approved on the Sahatak Telemedicine Platform.

            You can now:
            - Set your availability schedule
            - Accept patient appointments
            - Conduct online consultations
            - Access patient appointment history

            Thank you for joining our healthcare community.

            Best regards,
            The Sahatak Team
            """
            send_email(
                to_email=doctor.user.email,
                subject=email_subject,
                body=email_body
            )
            
        else:
            # rejection
            if not notes:
                return APIResponse.error(
                    message="Rejection notes are required",
                    status_code=400,
                    error_code="REJECTION_NOTES_REQUIRED"
                )
            
            doctor.verification_notes = notes
            doctor.rejection_date = datetime.utcnow()
            doctor.rejected_by = current_user.id
            
            # Send rejection email
            email_subject = "Doctor Verification - Additional Information Required"
            email_body = f"""
            Dear Dr. {doctor.user.full_name},

            Thank you for your application to join the Sahatak Telemedicine Platform.

            We need additional information or documentation before we can approve your account:

            {notes}

            Please update your profile with the requested information and we will review your application again.

            If you have any questions, please contact our support team.

            Best regards,
            The Sahatak Team
            """
            
            send_email(
                to_email=doctor.user.email,
                subject=email_subject,
                body=email_body
            )
        
    try:
        db.session.commit()
        
    # Log admin action
        log_user_action(
            current_user.id,
            'admin_verify_doctor',
            {
                'doctor_id': doctor_id,
                'approved': approved,
                'notes': notes
                'verification_date': datetime.utcnow().isoformat()
            }
        )
            
        # Queue notification to doctor
        notification_title = f"Application {'Approved' if approved else 'Needs Attention'}"
        notification_message = f"Your doctor verification has been {'approved' if approved else 'reviewed'}. Check your email for details."
            
        queue_notification(
            user_id=doctor.user_id,
            title=notification_title,
            message=notification_message,
            notification_type='success' if approved else 'warning',
            send_email=False,  # Already sent detailed email above
            send_sms=True if approved else False
            )
            
        return APIResponse.success(
            data={
                'doctor_id': doctor_id,
                'verified': approved,
                'verification_date': doctor.verification_date.isoformat() if approved else None,
                'notes': notes
            },
            message=f"Doctor {'verified' if approved else 'rejected'} successfully"
        )
        
    except Exception as e:
        app_logger.error(f"Admin verify doctor error: {str(e)}")
        return APIResponse.error(
            message="Failed to verify doctor",
            status_code=500
        )

#add a verified doctor
@admin_bp.route('/doctors', methods=['POST'])
@login_required
@admin_required
def add_doctor_manually(): 
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error(
                message="Request body required",
                status_code=400
            )
        
        # Validate required fields
        required_fields = ['email', 'full_name', 'password', 'specialty', 'license_number', 'years_of_experience']
        for field in required_fields:
            if not data.get(field):
                return APIResponse.error(
                    message=f"Field '{field}' is required",
                    status_code=400,
                    error_code="MISSING_REQUIRED_FIELD"
                )
        # Validate email format
        email = data['email'].lower().strip()
        if not validate_email(email):
            return APIResponse.error(
                message="Invalid email format",
                status_code=400,
                error_code="INVALID_EMAIL"
            )
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return APIResponse.error(
                message="Email already exists",
                status_code=400,
                error_code="EMAIL_EXISTS"
            )
        
        # Validate password
        password = data['password']
        if not validate_password(password):
            return APIResponse.error(
                message="Password does not meet requirements",
                status_code=400,
                error_code="WEAK_PASSWORD"
            )
        
        # Validate years of experience
        years_of_experience = data.get('years_of_experience', 10)
        if not isinstance(years_of_experience, int) or years_of_experience < 10:
            return APIResponse.error(
                message="Invalid years of experience",
                status_code=400
            )

    try:
            # Create User account
        new_user = User(
            email=email,
            full_name=data['full_name'].strip(),
            phone=data.get('phone', '').strip(),
            user_type='doctor',
            is_active=True,
            is_verified=True,
            profile_completed=True,
            created_at=datetime.utcnow()
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()  # Get user ID
            
            # Create Doctor profile
        new_doctor = Doctor(
            user_id=new_user.id,
            specialty=data['specialty'].strip(),
            license_number=data['license_number'].strip(),
            years_of_experience=years_of_experience,
            bio=data.get('bio', '').strip(),
            consultation_fee=data.get('consultation_fee', 0),
            is_verified=True,
            verification_date=datetime.utcnow(),
            verified_by=current_user.id,
            verification_notes=f"Manually added by admin {current_user.email}",
            created_at=datetime.utcnow()
        )
        db.session.add(new_doctor)
            
        db.session.commit()
            
            # Send welcome email with login credentials
        welcome_subject = "Welcome to Sahatak Telemedicine Platform"
        welcome_body = f"""
            Dear Dr. {new_user.full_name},

            Welcome to the Sahatak Telemedicine Platform! Your doctor account has been created and verified.

            Your login credentials:
            Email: {email}
            Password: {password}

            Please login to your account and:
            1. Change your password
            2. Complete your profile information  
            3. Set your availability schedule
            4. Upload your profile photo and documents

            You can start accepting patient appointments immediately.

            Login at: {current_app.config.get('FRONTEND_URL', '')}/login

            Best regards,
            The Sahatak Team
            """ 
         
        send_email(
                to_email=email,
                subject=welcome_subject,
                body=welcome_body
        )
            
            # Log admin action
        log_user_action(
            current_user.id,
                'admin_add_doctor_manually',
                {
                    'new_doctor_id': new_doctor.id,
                    'new_user_id': new_user.id,
                    'email': email,
                    'specialty': data['specialty'],
                    'license_number': data['license_number']
                }
        )
        
        return APIResponse.success(
            data={'message': 'Doctor added successfully'},
            message="Doctor created and verified"
        )
        
    except Exception as e:
            app_logger.error(f"Admin add doctor error: {str(e)}")
            return APIResponse.error(
                message="Failed to add doctor",
                status_code=500
            )

# =============================================================================
# SYSTEM SETTINGS ENDPOINTS
# =============================================================================
# current system settings
@admin_bp.route('/settings', methods=['GET'])
@login_required
@admin_required
def get_system_settings():
    try:
    # Get settings from database or return defaults
        settings_data = {}
        
        settings_query = setting.query.all()
        for setting in settings_query:
            settings_data[setting.key] = {
                'value': setting.value,
                'data_type': setting.data_type,
                'description': setting.description,
                'updated_at': setting.updated_at.isoformat(),
                'updated_by': setting.updated_by
            }
            
    # Add default settings if not in database
        default_settings = {
            'maintenance_mode': {'value': False, 'type': 'boolean', 'desc': 'Enable maintenance mode'},
            'registration_enabled': {'value': True, 'type': 'boolean', 'desc': 'Allow new user registration'},
            'default_language': {'value': 'ar', 'type': 'string', 'desc': 'Default platform language'},
            'max_appointment_days_ahead': {'value': 30, 'type': 'integer', 'desc': 'Maximum days ahead for booking'},
            'session_timeout_minutes': {'value': 60, 'type': 'integer', 'desc': 'User session timeout'},
            'password_min_length': {'value': 8, 'type': 'integer', 'desc': 'Minimum password length'},
            'max_login_attempts': {'value': 5, 'type': 'integer', 'desc': 'Max failed login attempts'},
            'consultation_duration_minutes': {'value': 30, 'type': 'integer', 'desc': 'Default consultation duration'},
            'platform_commission_percent': {'value': 10.0, 'type': 'float', 'desc': 'Platform commission percentage'},
            'email_notifications_enabled': {'value': True, 'type': 'boolean', 'desc': 'Enable email notifications'},
            'sms_notifications_enabled': {'value': True, 'type': 'boolean', 'desc': 'Enable SMS notifications'}
        }
        
        for key, config in default_settings.items():
            if key not in settings_data:
                settings_data[key] = {
                    'value': config['value'],
                    'data_type': config['type'],
                    'description': config['desc'],
                    'updated_at': None,
                    'updated_by': None
                }
        
        log_user_action(
            current_user.id,
            'admin_view_settings',
            {'settings_count': len(settings_data)}
        )
        
        return APIResponse.success(
            data={'settings': settings_data},
            message="System settings retrieved"
        )
        
    except Exception as e:
        app_logger.error(f"Admin get settings error: {str(e)}")
        return APIResponse.error(
            message="Failed to retrieve settings",
            status_code=500
        )

@admin_bp.route('/settings', methods=['PUT'])
@login_required
@admin_required
def update_system_settings():
# Update system settings
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error(
                message="Request body required",
                status_code=400
            )
        
        updated_settings = []
        validation_errors = []
        
        # Define setting validation rules
        setting_rules = {
            'maintenance_mode': {'type': bool, 'required': False},
            'registration_enabled': {'type': bool, 'required': False},
            'default_language': {'type': str, 'required': False, 'choices': ['ar', 'en']},
            'max_appointment_days_ahead': {'type': int, 'required': False, 'min': 1, 'max': 365},
            'session_timeout_minutes': {'type': int, 'required': False, 'min': 15, 'max': 480},
            'password_min_length': {'type': int, 'required': False, 'min': 6, 'max': 50},
            'max_login_attempts': {'type': int, 'required': False, 'min': 3, 'max': 20},
            'consultation_duration_minutes': {'type': int, 'required': False, 'min': 15, 'max': 180},
            'platform_commission_percent': {'type': float, 'required': False, 'min': 0.0, 'max': 50.0},
            'email_notifications_enabled': {'type': bool, 'required': False},
            'sms_notifications_enabled': {'type': bool, 'required': False}
        }
        
        # Validate each setting
        for key, value in data.items():
            if key not in setting_rules:
                validation_errors.append(f"Unknown setting: {key}")
                continue
            
            rule = setting_rules[key]
            
            # Type validation
            if not isinstance(value, rule['type']):
                try:
                    if rule['type'] == bool:
                        value = str(value).lower() in ['true', '1', 'yes', 'on']
                    elif rule['type'] == int:
                        value = int(value)
                    elif rule['type'] == float:
                        value = float(value)
                    else:
                        value = str(value)
                except (ValueError, TypeError):
                    validation_errors.append(f"Invalid type for {key}")
                    continue
            
            # Range validation
            if rule['type'] in [int, float]:
                if 'min' in rule and value < rule['min']:
                    validation_errors.append(f"{key} must be at least {rule['min']}")
                    continue
                if 'max' in rule and value > rule['max']:
                    validation_errors.append(f"{key} must be at most {rule['max']}")
                    continue
            
            # Choice validation
            if 'choices' in rule and value not in rule['choices']:
                validation_errors.append(f"{key} must be one of: {rule['choices']}")
                continue
            
            updated_settings.append((key, value, rule['type'].__name__))
        
        if validation_errors:
            return APIResponse.error(
                message="Settings validation failed",
                status_code=400,
                error_code="VALIDATION_ERROR",
                details=validation_errors
            )
        
    try:
            # Update settings in database
        for key, value, data_type in updated_settings:
            setting = SystemSettings.query.filter_by(key=key).first()
                
            if setting:
                setting.value = str(value)
                setting.data_type = data_type
                setting.updated_at = datetime.utcnow()
                setting.updated_by = current_user.id
            else:
                new_setting = SystemSettings(
                    key=key,
                    value=str(value),
                    data_type=data_type,
                    description=f"Updated by admin {current_user.email}",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    updated_by=current_user.id
                )
                db.session.add(new_setting)
            
        db.session.commit()
            
            # Log admin action
        log_user_action(
                current_user.id,
                'admin_update_settings',
                {
                    'updated_settings': [key for key, _, _ in updated_settings],
                    'settings_count': len(updated_settings)
                }
            )
        
        log_user_action(
            current_user.id,
            'admin_update_settings',
            {'updated_settings': list(data.keys())}
        )
        
        return APIResponse.success(
            message="System settings updated successfully"
        )
        
    except Exception as e:
        app_logger.error(f"Admin update settings error: {str(e)}")
        return APIResponse.error(
            message="Failed to update settings",
            status_code=500
        )

# =============================================================================
# PLATFORM HEALTH & ANALYTICS ENDPOINTS
# =============================================================================

@admin_bp.route('/health/detailed', methods=['GET'])
@login_required
@admin_required
def get_detailed_health():
    try:
        
        start_time = datetime.utcnow()
        
        # Database health check
        db_start = datetime.utcnow()
        try:
            db.session.execute(text('SELECT 1'))
            db_time = (datetime.utcnow() - db_start).total_seconds() * 1000
            db_status = 'healthy'
            db_error = None
        except Exception as e:
            db_time = (datetime.utcnow() - db_start).total_seconds() * 1000
            db_status = 'unhealthy'
            db_error = str(e)
        
        # Get database connection info
        try:
            active_connections = db.session.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            ).scalar()
        except:
            active_connections = 'unknown'
        
        # Calculate API metrics for last 24 hours
        try:
            twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
            
            # Get error rate from audit logs
            total_requests = AuditLog.query.filter(
                AuditLog.created_at >= twenty_four_hours_ago
            ).count()
            
            error_requests = AuditLog.query.filter(
                and_(
                    AuditLog.created_at >= twenty_four_hours_ago,
                    AuditLog.action.like('%error%')
                )
            ).count()
            
            error_rate = (error_requests / total_requests) if total_requests > 0 else 0
            
        except:
            total_requests = 'unknown'
            error_rate = 'unknown'
        
        # System resource usage (basic estimates)
        import psutil
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            system_info = {
                'cpu_usage_percent': cpu_usage,
                'memory_usage_percent': memory.percent,
                'disk_usage_percent': disk.percent,
                'uptime_hours': (datetime.utcnow() - start_time).total_seconds() / 3600
            }
        except ImportError:
            # Fallback if psutil not available
            system_info = {
                'cpu_usage_percent': 'unavailable',
                'memory_usage_percent': 'unavailable', 
                'disk_usage_percent': 'unavailable',
                'uptime_hours': 'unavailable'
            }
        
        health_data = {
            'database': {
                'status': db_status,
                'connection_time_ms': round(db_time, 20),
                'active_connections': active_connections,
                'error': db_error
            },
            'api': {
                'avg_response_time_ms': round((datetime.utcnow() - start_time).total_seconds() * 1000, 2),
                'error_rate_24h': round(error_rate, 20) if isinstance(error_rate, float) else error_rate,
                'total_requests_24h': total_requests
            },
            'system': system_info,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        log_user_action(
            current_user.id,
            'admin_view_detailed_health',
            {'db_status': db_status, 'system_check': True}
        )
        
        return APIResponse.success(
            data={'health': health_data},
            message="Detailed health information retrieved"
        )
        
    except Exception as e:
        app_logger.error(f"Admin get detailed health error: {str(e)}")
        return APIResponse.error(
            message="Failed to retrieve health information",
            status_code=500
        )

@admin_bp.route('/analytics/dashboard', methods=['GET'])
@login_required
@admin_required
def get_dashboard_analytics():
    try:
        period = request.args.get('period', 'week')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Define time ranges
        now = datetime.utcnow()
        if period == 'day':
            period_start = now - timedelta(days=1)
        elif period == 'week':
            period_start = now - timedelta(weeks=1)
        elif period == 'month':
            period_start = now - timedelta(days=30)
        elif period == 'year':
            period_start = now - timedelta(days=365)
        elif start_date and end_date:
            period_start, period_end = validate_date_range(start_date, end_date)
            if not period_end:
                period_end = now
        else:
            period_start = now - timedelta(weeks=1)
            period_end = now
        
        if 'period_end' not in locals():
            period_end = now
        
        # User statistics
        new_registrations = User.query.filter(
            User.created_at >= period_start
        ).count()
        
        active_users = User.query.filter(
            and_(
                User.is_active == True,
                User.last_login >= period_start
            )
        ).count()
        
        # Calculate growth rate
        previous_period_start = period_start - (period_end - period_start)
        previous_users = User.query.filter(
            User.created_at <= period_start
        ).count()
        
        user_growth_rate = ((previous_users) / previous_users * 100) if previous_users > 0 else 0
        
        # Appointment statistics
        total_appointments = Appointment.query.count()
        period_appointments = Appointment.query.filter(
            Appointment.created_at >= period_start
        ).count()
        
        completed_appointments = Appointment.query.filter(
            and_(
                Appointment.created_at >= period_start,
                Appointment.status == 'completed'
            )
        ).count()
        
        cancelled_appointments = Appointment.query.filter(
            and_(
                Appointment.created_at >= period_start,
                Appointment.status == 'cancelled'
            )
        ).count()
        
        # Doctor statistics
        total_doctors = Doctor.query.count()
        verified_doctors = Doctor.query.filter_by(is_verified=True).count()
        
        active_doctors = Doctor.query.join(User).filter(
            and_(
                Doctor.is_verified == True,
                User.is_active == True,
                User.last_login >= period_start
            )
        ).count()
        
        # Average appointments per doctor
        if verified_doctors > 0:
            avg_appointments_per_doctor = db.session.query(
                func.avg(func.coalesce(Doctor.total_consultations, 0))
            ).filter(Doctor.is_verified == True).scalar() or 0
        else:
            avg_appointments_per_doctor = 0
        
        # Platform usage patterns
        try:
            # Peak usage hour (simplified - based on appointment creation times)
            hourly_usage = db.session.query(
                func.extract('hour', Appointment.created_at).label('hour'),
                func.count(Appointment.id).label('count')
            ).filter(
                Appointment.created_at >= period_start
            ).group_by(func.extract('hour', Appointment.created_at)).all()
            
            peak_hour = max(hourly_usage, key=lambda x: x.count).hour if hourly_usage else 14
            
            # Most used features (based on audit logs)
            feature_usage = db.session.query(
                AuditLog.action,
                func.count(AuditLog.id).label('usage_count')
            ).filter(
                AuditLog.created_at >= period_start
            ).group_by(AuditLog.action).order_by(
                func.count(AuditLog.id).desc()
            ).limit(5).all()
            
            most_used_features = [action for action, count in feature_usage]
            
        except:
            peak_hour = 14
            most_used_features = ['appointments', 'consultations', 'profile']
        
        # Geographic distribution (if available)
        try:
            city_distribution = db.session.query(
                Patient.city,
                func.count(Patient.id).label('count')
            ).filter(
                Patient.city.isnot(None)
            ).group_by(Patient.city).order_by(
                func.count(Patient.id).desc()
            ).limit(10).all()
            
            top_cities = [{'city': city, 'users': count} for city, count in city_distribution]
        except:
            top_cities = []
        
        analytics_data = {
            'user_stats': {
                'new_registrations_period': new_registrations,
                'active_users_period': active_users,
                'user_growth_rate': round(user_growth_rate, 2)
            },
            'appointment_stats': {
                'total_appointments': total_appointments,
                'appointments_period': period_appointments,
                'completed_appointments': completed_appointments,
                'cancelled_appointments': cancelled_appointments,
                'completion_rate': round((completed_appointments / period_appointments * 100) if period_appointments > 0 else 0, 2)
            },
            'doctor_stats': {
                'total_doctors': total_doctors,
                'verified_doctors': verified_doctors,
                'active_doctors_period': active_doctors,
                'avg_appointments_per_doctor': round(avg_appointments_per_doctor, 1),
                'verification_rate': round((verified_doctors / total_doctors * 100) if total_doctors > 0 else 0, 2)
            },
            'platform_usage': {
                'peak_usage_hour': int(peak_hour),
                'avg_session_duration_minutes': 25,  # This would need session tracking
                'bounce_rate': 0.15,  # This would need proper analytics
                'most_used_features': most_used_features
            },
            'geographic_data': {
                'top_cities': top_cities
            },
            'period_info': {
                'period': period,
                'start_date': period_start.isoformat(),
                'end_date': period_end.isoformat(),
                'days_included': (period_end - period_start).days
            }
        }
        
        log_user_action(
            current_user.id,
            'admin_view_analytics',
            {'period': period, 'data_points_calculated': len(analytics_data)}
        )
        
        return APIResponse.success(
            data={'analytics': analytics_data},
            message="Dashboard analytics retrieved"
        )
        
    except Exception as e:
        app_logger.error(f"Admin get analytics error: {str(e)}")
        return APIResponse.error(
            message="Failed to retrieve analytics",
            status_code=500
        )

# =============================================================================
# SYSTEM NOTIFICATIONS ENDPOINTS
# =============================================================================

@admin_bp.route('/notifications/broadcast', methods=['POST'])
@login_required
@admin_required
def send_broadcast_notification():
# Send notification to all users or specific groups
   
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error(
                message="Request body required",
                status_code=400
            )
        
    # Validate required fields
        title = data.get('title', '').strip()
        message = data.get('message', '').strip()
        
        if not title or not message:
            return APIResponse.error(
                message="Title and message are required",
                status_code=400,
                error_code="MISSING_REQUIRED_FIELDS"
            )
        
        if len(title) > 100:
            return APIResponse.error(
                message="Title must be less than 100 characters",
                status_code=400,
                error_code="TITLE_TOO_LONG"
            )
        
        if len(message) > 1000:
            return APIResponse.error(
                message="Message must be less than 1000 characters",
                status_code=400,
                error_code="MESSAGE_TOO_LONG"
            )
            
    # Validate target audience
        target = data.get('target', 'all')
        valid_targets = ['all', 'patients', 'doctors', 'admins']
        if target not in valid_targets:
            return APIResponse.error(
                message=f"Target must be one of: {valid_targets}",
                status_code=400,
                error_code="INVALID_TARGET"
            )
            
    # Validate notification type
        notification_type = data.get('type', 'info')
        valid_types = ['info', 'warning', 'urgent', 'success']
        if notification_type not in valid_types:
            return APIResponse.error(
                message=f"Type must be one of: {valid_types}",
                status_code=400,
                error_code="INVALID_TYPE"
            )
            
    # Validate delivery options
        send_email = data.get('send_email', False)
        send_sms = data.get('send_sms', False)
        
        if not send_email and not send_sms:
            return APIResponse.error(
                message="At least one delivery method (email or SMS) must be selected",
                status_code=400,
                error_code="NO_DELIVERY_METHOD"
            )
            
    # Validate schedule time if provided
        schedule_time = data.get('schedule_time')
        if schedule_time:
            try:
                schedule_datetime = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
                if schedule_datetime <= datetime.utcnow():
                    return APIResponse.error(
                        message="Schedule time must be in the future",
                        status_code=400,
                        error_code="INVALID_SCHEDULE_TIME"
                    )
            except ValueError:
                return APIResponse.error(
                    message="Invalid schedule time format",
                    status_code=400,
                    error_code="INVALID_DATETIME_FORMAT"
                )
        else:
            schedule_datetime = None
            
    # Build target user query
        base_query = User.query.filter(User.is_active == True)
        
        if target == 'patients':
            target_users = base_query.filter(User.user_type == 'patient').all()
        elif target == 'doctors':
            target_users = base_query.filter(User.user_type == 'doctor').all()
        elif target == 'admins':
            target_users = base_query.filter(User.user_type == 'admin').all()
        else:  # target == 'all'
            target_users = base_query.all()
        
        if not target_users:
            return APIResponse.error(
                message=f"No active users found for target: {target}",
                status_code=400,
                error_code="NO_TARGET_USERS"
            )
            
     # Queue notifications for each target user
        notifications_queued = 0
        failed_notifications = 0
        
        for user in target_users:
            try:
                queue_notification(
                    user_id=user.id,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    send_email=send_email,
                    send_sms=send_sms,
                    scheduled_time=schedule_datetime,
                    sender_id=current_user.id,
                    metadata={
                        'broadcast_id': f"broadcast_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                        'admin_sender': current_user.email,
                        'target_group': target
                    }
                )
                notifications_queued += 1
                
            except Exception as e:
                app_logger.error(f"Failed to queue notification for user {user.id}: {str(e)}")
                failed_notifications += 1
                
                 # Log admin action
        log_user_action(
            current_user.id,
            'admin_broadcast_notification',
            {
                'title': title,
                'message_length': len(message),
                'target': target,
                'type': notification_type,
                'send_email': send_email,
                'send_sms': send_sms,
                'scheduled': bool(schedule_datetime),
                'schedule_time': schedule_datetime.isoformat() if schedule_datetime else None,
                'notifications_queued': notifications_queued,
                'failed_notifications': failed_notifications,
                'target_user_count': len(target_users)
            }
        )
        
    # Prepare response message
        if schedule_datetime:
            status_message = f"Broadcast notification scheduled for {schedule_datetime.isoformat()}"
        else:
            status_message = "Broadcast notification sent successfully"
        
        return APIResponse.success(
            data={
                'broadcast_id': f"broadcast_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'notifications_queued': notifications_queued,
                'failed_notifications': failed_notifications,
                'target_users': len(target_users),
                'scheduled': bool(schedule_datetime),
                'schedule_time': schedule_datetime.isoformat() if schedule_datetime else None
            },
            message=status_message
        )
    except Exception as e:
        app_logger.error(f"Admin broadcast notification error: {str(e)}")
        return APIResponse.error(
            message="Failed to send broadcast notification",
            status_code=500
        )

# =============================================================================
# AUDIT LOG ENDPOINTS
# =============================================================================

@admin_bp.route('/audit-logs', methods=['GET'])
@login_required
@admin_required
def get_audit_logs():
# Get detailed information for a specific audit log entry

    try:
        log_entry = AuditLog.query.options(
            joinedload(AuditLog.user)
        ).get(log_entry)
        
        if not log_entry:
            return APIResponse.error(
                message="Audit log entry not found",
                status_code=404,
                error_code="AUDIT_LOG_NOT_FOUND"
            )
            
            # Format detailed log information
        log_details = {
            'id': log_entry.id,
            'action': log_entry.action,
            'user_id': log_entry.user_id,
            'user_info': {
                'email': log_entry.user.email if log_entry.user else 'System',
                'full_name': log_entry.user.full_name if log_entry.user else 'System',
                'user_type': log_entry.user.user_type if log_entry.user else 'system',
                'is_active': log_entry.user.is_active if log_entry.user else None
            },
            'request_info': {
                'ip_address': log_entry.ip_address,
                'user_agent': log_entry.user_agent,
                'method': getattr(log_entry, 'method', None),
                'endpoint': getattr(log_entry, 'endpoint', None)
            },
            'details': log_entry.details if log_entry.details else {},
            'timestamps': {
                'created_at': log_entry.created_at.isoformat(),
                'created_at_readable': log_entry.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'days_ago': (datetime.utcnow() - log_entry.created_at).days
            }
        }
        
    # Determine severity and risk level
        action_lower = log_entry.action.lower()
        if any(keyword in action_lower for keyword in ['error', 'failed', 'denied', 'blocked']):
            log_details['severity'] = 'error'
        elif any(keyword in action_lower for keyword in ['warning', 'attempt', 'locked']):
            log_details['severity'] = 'warning'
        else:
            log_details['severity'] = 'info'
        
        if any(keyword in action_lower for keyword in ['login_failed', 'account_locked', 'admin_access_denied']):
            log_details['risk_level'] = 'high'
        elif any(keyword in action_lower for keyword in ['password_changed', 'profile_updated', 'admin_']):
            log_details['risk_level'] = 'medium'
        else:
            log_details['risk_level'] = 'low'
        
    # Get related logs (same user, similar timeframe)
        if log_entry.user_id:
            related_logs = AuditLog.query.filter(
                and_(
                    AuditLog.user_id == log_entry.user_id,
                    AuditLog.id != log_entry.id,
                    AuditLog.created_at >= log_entry.created_at - timedelta(hours=1),
                    AuditLog.created_at <= log_entry.created_at + timedelta(hours=1)
                )
            ).order_by(AuditLog.created_at.desc()).limit(5).all()
            
            log_details['related_logs'] = [{
                'id': related.id,
                'action': related.action,
                'created_at': related.created_at.isoformat(),
                'ip_address': related.ip_address
            } for related in related_logs]
        else:
            log_details['related_logs'] = []
            
    # Log this admin action
        log_user_action(
            current_user.id,
            'admin_view_audit_log_details',
            {
                'audit_log_id': log_entry,
                'target_action': log_entry.action,
                'target_user_id': log_entry.user_id
            }
        )
        
        return APIResponse.success(
            data={'audit_log': log_details},
            message="Audit log details retrieved"
        )

    except Exception as e:
        app_logger.error(f"Admin get audit logs error: {str(e)}")
        return APIResponse.error(
            message="Failed to retrieve audit logs",
            status_code=500
        )

# =============================================================================
# IMPLEMENTATION NOTES FOR AHMED
# =============================================================================

"""
AHMED - IMPLEMENTATION CHECKLIST:

1. DATABASE MODELS TO CREATE:
   - Admin model (extend User or add admin role)
   - SystemSettings model
   - AuditLog model
   - NotificationQueue model

2. SECURITY REQUIREMENTS:
   - Implement proper admin authentication
   - Add permission checks for all endpoints
   - Never expose patient medical records
   - Log all admin actions for audit trails
   - Implement rate limiting for admin endpoints

3. EMAIL/SMS INTEGRATION:
   - Set up email templates for doctor verification
   - Implement SMS notifications for urgent broadcasts
   - Create notification queue system

4. ANALYTICS IMPLEMENTATION:
   - Create database views for efficient analytics
   - Implement caching for frequently accessed metrics
   - Consider using background jobs for heavy calculations

5. ERROR HANDLING:
   - Add comprehensive input validation
   - Handle database constraints properly
   - Provide meaningful error messages
   - Log all errors with context

6. PERFORMANCE CONSIDERATIONS:
   - Add database indexes for admin queries
   - Implement pagination for all list endpoints
   - Use database connection pooling
   - Cache frequently accessed settings

7. TESTING:
   - Write unit tests for all admin functions
   - Test admin authentication thoroughly
   - Verify data privacy requirements
   - Test error scenarios

8. DEPLOYMENT:
   - Add admin endpoints to main app.py
   - Update CORS settings if needed
   - Configure admin-specific environment variables
   - Document admin API endpoints

Remember: The admin system should be powerful but secure.
Never compromise on data privacy or security!
"""