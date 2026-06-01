from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.utils.timezone import now
from datetime import datetime, date, timedelta
from .models import PatientProfile, DoctorProfile, DoctorAvailability, Appointment, SPECIALIZATIONS
from .forms import PatientRegistrationForm, DoctorNotesForm

def send_booking_email(appointment, action='booked'):
    """
    Simulates sending emails to both patient and doctor.
    Outputs to console (defined in settings EMAIL_BACKEND).
    """
    subject = f"[Antigravity Hospital] Appointment {action.upper()}: {appointment.date}"
    
    patient_email = appointment.patient.user.email
    doctor_email = appointment.doctor.user.email
    
    patient_name = appointment.patient.user.get_full_name() or appointment.patient.user.username
    doctor_name = appointment.doctor.user.get_full_name() or appointment.doctor.user.username
    
    if action == 'booked':
        message = (
            f"Dear {patient_name},\n\n"
            f"Your appointment with Dr. {doctor_name} ({appointment.doctor.specialization}) has been confirmed.\n"
            f"Date: {appointment.date}\n"
            f"Time: {appointment.time_slot.strftime('%I:%M %p')}\n"
            f"Reason: {appointment.symptoms or 'General consultation'}\n\n"
            f"Please arrive 15 minutes early.\n\n"
            f"Warm regards,\n"
            f"Antigravity Clinic Services"
        )
    elif action == 'cancelled':
        message = (
            f"Dear {patient_name},\n\n"
            f"We confirm that your appointment with Dr. {doctor_name} on {appointment.date} has been CANCELLED.\n\n"
            f"If you wish to reschedule, please visit our online portal.\n\n"
            f"Warm regards,\n"
            f"Antigravity Clinic Services"
        )
    elif action == 'completed':
        message = (
            f"Dear {patient_name},\n\n"
            f"Your appointment with Dr. {doctor_name} has been marked as Completed.\n"
            f"Dr. {doctor_name} has left clinical notes and prescriptions in your dashboard.\n\n"
            f"Notes:\n{appointment.doctor_notes or 'None'}\n\n"
            f"Wishing you good health,\n"
            f"Antigravity Clinic Services"
        )
    else:
        message = f"Details updated for your appointment on {appointment.date}."

    # Send to Patient
    send_mail(
        subject,
        message,
        'no-reply@hospitalbooking.com',
        [patient_email],
        fail_silently=True
    )

    # Send to Doctor
    doc_subject = f"[Clinic Alert] Appointment {action.upper()}: Patient {patient_name}"
    doc_message = (
        f"Dear Dr. {doctor_name},\n\n"
        f"An appointment for {appointment.date} at {appointment.time_slot.strftime('%I:%M %p')} has been {action}.\n"
        f"Patient Name: {patient_name}\n"
        f"Details: {appointment.symptoms or 'General checkup'}\n"
    )
    send_mail(
        doc_subject,
        doc_message,
        'no-reply@hospitalbooking.com',
        [doctor_email],
        fail_silently=True
    )

def home(request):
    query = request.GET.get('q', '')
    specialization = request.GET.get('specialization', '')
    
    doctors = DoctorProfile.objects.all()
    if query:
        doctors = doctors.filter(user__first_name__icontains=query) | doctors.filter(user__last_name__icontains=query)
    if specialization:
        doctors = doctors.filter(specialization=specialization)
        
    context = {
        'doctors': doctors,
        'specializations': [spec[0] for spec in SPECIALIZATIONS],
        'selected_specialization': specialization,
        'query': query,
    }
    return render(request, 'booking/home.html', context)

def register_patient(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created successfully! Welcome, {user.first_name}.")
            return redirect('patient_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PatientRegistrationForm()
    return render(request, 'booking/register.html', {'form': form})

def login_user(request):
    if request.user.is_authenticated:
        # Redirect based on user group/profile
        if hasattr(request.user, 'doctor_profile'):
            return redirect('doctor_dashboard')
        return redirect('patient_dashboard')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                if hasattr(user, 'doctor_profile'):
                    return redirect('doctor_dashboard')
                return redirect('patient_dashboard')
        messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'booking/login.html', {'form': form})

def logout_user(request):
    logout(request)
    messages.info(request, "You have logged out successfully.")
    return redirect('home')

def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    
    # Selected date for availability check (default is tomorrow)
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = date.today() + timedelta(days=1)
    else:
        selected_date = date.today() + timedelta(days=1)
        
    # Prevent booking past dates
    if selected_date < date.today():
        selected_date = date.today()
        
    slots = doctor.get_slots_for_date(selected_date)
    weekday_name = selected_date.strftime('%A')
    
    context = {
        'doctor': doctor,
        'selected_date': selected_date,
        'slots': slots,
        'weekday_name': weekday_name,
        'min_date': date.today().strftime('%Y-%m-%d'),
        'max_date': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
    }
    return render(request, 'booking/doctor_detail.html', context)

@login_required
def book_appointment(request, doctor_id):
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, "Only registered patients can book appointments.")
        return redirect('home')
        
    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    
    if request.method == 'POST':
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')
        symptoms = request.POST.get('symptoms', '')
        
        try:
            booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            booking_time = datetime.strptime(time_str, '%H:%M:%S').time()
        except (ValueError, TypeError):
            messages.error(request, "Invalid date or time slot selected.")
            return redirect('doctor_detail', doctor_id=doctor.id)
            
        # Validations
        if booking_date < date.today():
            messages.error(request, "Cannot book appointments in the past.")
            return redirect('doctor_detail', doctor_id=doctor.id)
            
        # Prevent same-day past-time bookings
        if booking_date == date.today() and booking_time < datetime.now().time():
            messages.error(request, "Cannot book a slot that has already passed.")
            return redirect('doctor_detail', doctor_id=doctor.id)
            
        # Check availability (is the doctor working, is it already booked?)
        slots = doctor.get_slots_for_date(booking_date)
        valid_slot = False
        for s in slots:
            if s['time'] == booking_time:
                if s['is_booked']:
                    messages.error(request, "This time slot is no longer available.")
                    return redirect('doctor_detail', doctor_id=doctor.id)
                valid_slot = True
                break
                
        if not valid_slot:
            messages.error(request, "The doctor is not available at the selected time.")
            return redirect('doctor_detail', doctor_id=doctor.id)
            
        # Create appointment
        patient = request.user.patient_profile
        try:
            appointment = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                date=booking_date,
                time_slot=booking_time,
                symptoms=symptoms
            )
            # Send Notification
            send_booking_email(appointment, action='booked')
            messages.success(request, f"Appointment successfully scheduled with Dr. {doctor.user.last_name}!")
            return redirect('patient_dashboard')
        except Exception as e:
            messages.error(request, f"Error booking appointment: {e}")
            return redirect('doctor_detail', doctor_id=doctor.id)
            
    return redirect('doctor_detail', doctor_id=doctor.id)

@login_required
def patient_dashboard(request):
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, "Dashboard only accessible to patients.")
        return redirect('home')
        
    patient = request.user.patient_profile
    appointments = Appointment.objects.filter(patient=patient)
    
    upcoming = appointments.filter(date__gte=date.today(), status='Scheduled').order_by('date', 'time_slot')
    past = appointments.exclude(id__in=upcoming.values_list('id', flat=True)).order_by('-date', '-time_slot')
    
    context = {
        'upcoming': upcoming,
        'past': past,
        'patient': patient,
    }
    return render(request, 'booking/patient_dashboard.html', context)

@login_required
def doctor_dashboard(request):
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, "Dashboard only accessible to Doctors.")
        return redirect('home')
        
    doctor = request.user.doctor_profile
    appointments = Appointment.objects.filter(doctor=doctor)
    
    today_bookings = appointments.filter(date=date.today()).order_by('time_slot')
    upcoming = appointments.filter(date__gt=date.today(), status='Scheduled').order_by('date', 'time_slot')
    past = appointments.filter(status__in=['Completed', 'Cancelled']).order_by('-date', '-time_slot')
    
    context = {
        'today_bookings': today_bookings,
        'upcoming': upcoming,
        'past': past,
        'doctor': doctor,
    }
    return render(request, 'booking/doctor_dashboard.html', context)

@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Security: Ensure only the associated patient or doctor can cancel
    is_patient = hasattr(request.user, 'patient_profile') and appointment.patient.user == request.user
    is_doctor = hasattr(request.user, 'doctor_profile') and appointment.doctor.user == request.user
    
    if not (is_patient or is_doctor):
        messages.error(request, "Unauthorized request.")
        return redirect('home')
        
    if appointment.status != 'Scheduled':
        messages.error(request, "Only scheduled appointments can be cancelled.")
    else:
        appointment.status = 'Cancelled'
        appointment.save()
        send_booking_email(appointment, action='cancelled')
        messages.success(request, "Appointment successfully cancelled.")
        
    if is_doctor:
        return redirect('doctor_dashboard')
    return redirect('patient_dashboard')

@login_required
def update_appointment_notes(request, appointment_id):
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, "Only doctors can update prescriptions/notes.")
        return redirect('home')
        
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user.doctor_profile)
    
    if request.method == 'POST':
        form = DoctorNotesForm(request.POST, instance=appointment)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.status = 'Completed' # Auto complete when notes are saved
            appointment.save()
            send_booking_email(appointment, action='completed')
            messages.success(request, f"Prescription updated and appointment with {appointment.patient.user.get_full_name()} marked as completed.")
        else:
            messages.error(request, "Failed to save prescription notes.")
            
    return redirect('doctor_dashboard')
