import datetime
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import PatientProfile, DoctorProfile, DoctorAvailability, Appointment

class HospitalSystemTests(TestCase):
    def setUp(self):
        # 1. Create Patient User & Profile
        self.patient_user = User.objects.create_user(
            username='test_patient',
            password='patientpassword',
            first_name='Alex',
            last_name='Jones',
            email='alex@example.com'
        )
        self.patient_profile = PatientProfile.objects.create(
            user=self.patient_user,
            phone_number='1234567890',
            date_of_birth=datetime.date(1995, 5, 20),
            gender='Male',
            blood_group='O+'
        )

        # 2. Create Doctor User & Profile
        self.doctor_user = User.objects.create_user(
            username='test_doctor',
            password='doctorpassword',
            first_name='Sarah',
            last_name='Connor',
            email='connor@example.com'
        )
        self.doctor_profile = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialization='Cardiology',
            bio='Cardiology expert with 10 years experience.',
            consultation_fee=120.00,
            experience_years=10
        )

        # 3. Create Doctor Availability (Monday 09:00 - 11:00)
        # Weekday 1 is Monday in our system choice list (dict index 1)
        self.availability = DoctorAvailability.objects.create(
            doctor=self.doctor_profile,
            day_of_week=1,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(11, 0)
        )

    def test_patient_profile_creation(self):
        """Verify PatientProfile maps to correct User and holds correct fields."""
        self.assertEqual(self.patient_profile.user.username, 'test_patient')
        self.assertEqual(self.patient_profile.phone_number, '1234567890')
        self.assertEqual(str(self.patient_profile), 'Alex Jones (Patient)')

    def test_doctor_profile_creation(self):
        """Verify DoctorProfile maps correctly and holds correct details."""
        self.assertEqual(self.doctor_profile.specialization, 'Cardiology')
        self.assertEqual(str(self.doctor_profile), 'Dr. Sarah Connor (Cardiology)')

    def test_slot_generation_for_date(self):
        """Verify get_slots_for_date generates correct 30-min slots based on doctor availability."""
        # Next Monday date
        today = datetime.date.today()
        # Find next Monday (isoweekday = 1)
        days_ahead = 1 - today.isoweekday()
        if days_ahead <= 0: # Already past Monday or is Monday today
            days_ahead += 7
        next_monday = today + datetime.timedelta(days_ahead)

        slots = self.doctor_profile.get_slots_for_date(next_monday)
        # 09:00 to 11:00 should have 4 slots: 09:00, 09:30, 10:00, 10:30
        self.assertEqual(len(slots), 4)
        
        # Verify slot structures
        self.assertEqual(slots[0]['time'], datetime.time(9, 0))
        self.assertFalse(slots[0]['is_booked'])
        self.assertEqual(slots[0]['formatted'], '09:00 AM')

        self.assertEqual(slots[3]['time'], datetime.time(10, 30))
        self.assertFalse(slots[3]['is_booked'])
        self.assertEqual(slots[3]['formatted'], '10:30 AM')

    def test_slot_booking_marks_unavailable(self):
        """Verify booking a slot marks it as booked/unavailable for that doctor on that date."""
        today = datetime.date.today()
        days_ahead = 1 - today.isoweekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = today + datetime.timedelta(days_ahead)

        # Create appointment on 09:30 AM slot
        appt_time = datetime.time(9, 30)
        Appointment.objects.create(
            patient=self.patient_profile,
            doctor=self.doctor_profile,
            date=next_monday,
            time_slot=appt_time,
            status='Scheduled'
        )

        slots = self.doctor_profile.get_slots_for_date(next_monday)
        # Slot index 1 should be 09:30 AM
        self.assertEqual(slots[1]['time'], appt_time)
        self.assertTrue(slots[1]['is_booked'])
        
        # Other slots should still be available
        self.assertFalse(slots[0]['is_booked'])

    def test_appointment_cancellation(self):
        """Verify appointment cancellation transitions status correctly."""
        appt = Appointment.objects.create(
            patient=self.patient_profile,
            doctor=self.doctor_profile,
            date=datetime.date.today(),
            time_slot=datetime.time(9, 0),
            status='Scheduled'
        )
        self.assertEqual(appt.status, 'Scheduled')
        
        # Client cancels
        self.client.login(username='test_patient', password='patientpassword')
        response = self.client.get(reverse('cancel_appointment', args=[appt.id]))
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'Cancelled')
