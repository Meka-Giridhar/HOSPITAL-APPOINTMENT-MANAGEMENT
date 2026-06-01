from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, date, timedelta, time

# Specialization choices
SPECIALIZATIONS = [
    ('General Medicine', 'General Medicine'),
    ('Cardiology', 'Cardiology'),
    ('Dermatology', 'Dermatology'),
    ('Pediatrics', 'Pediatrics'),
    ('Neurology', 'Neurology'),
    ('Orthopedics', 'Orthopedics'),
    ('Ophthalmology', 'Ophthalmology'),
    ('Gynecology', 'Gynecology'),
]

# Gender choices
GENDER_CHOICES = [
    ('Male', 'Male'),
    ('Female', 'Female'),
    ('Other', 'Other'),
]

# Appointment Status choices
STATUS_CHOICES = [
    ('Scheduled', 'Scheduled'),
    ('Completed', 'Completed'),
    ('Cancelled', 'Cancelled'),
]

# Day of Week choices
WEEKDAY_CHOICES = [
    (1, 'Monday'),
    (2, 'Tuesday'),
    (3, 'Wednesday'),
    (4, 'Thursday'),
    (5, 'Friday'),
    (6, 'Saturday'),
    (7, 'Sunday'),
]

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    phone_number = models.CharField(max_length=15)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    blood_group = models.CharField(max_length=5, blank=True, null=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} (Patient)"

class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.CharField(max_length=50, choices=SPECIALIZATIONS)
    bio = models.TextField()
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2)
    experience_years = models.PositiveIntegerField()
    profile_picture_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username} ({self.specialization})"

    def get_slots_for_date(self, book_date):
        """
        Generates 30-minute slots based on doctor availability for book_date's weekday,
        and marks them as booked/available based on existing appointments.
        Returns a list of dicts: [{'time': time_object, 'is_booked': bool, 'formatted': '09:00 AM'}]
        """
        weekday = book_date.isoweekday() # 1 = Monday, ..., 7 = Sunday
        availabilities = self.availabilities.filter(day_of_week=weekday)
        
        # Get existing appointments for this doctor on this date
        booked_times = set(
            Appointment.objects.filter(
                doctor=self,
                date=book_date,
                status__in=['Scheduled', 'Completed']
            ).values_list('time_slot', flat=True)
        )
        
        slots = []
        for avail in availabilities:
            start_dt = datetime.combine(book_date, avail.start_time)
            end_dt = datetime.combine(book_date, avail.end_time)
            
            curr = start_dt
            while curr + timedelta(minutes=30) <= end_dt:
                slot_time = curr.time()
                is_booked = slot_time in booked_times
                
                # Check if slot is in the past for today
                is_past = False
                if book_date == date.today():
                    is_past = slot_time < datetime.now().time()
                
                slots.append({
                    'time': slot_time,
                    'is_booked': is_booked or is_past,
                    'formatted': slot_time.strftime('%I:%M %p')
                })
                curr += timedelta(minutes=30)
        
        # Sort slots by time
        slots.sort(key=lambda s: s['time'])
        return slots

class DoctorAvailability(models.Model):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.IntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        verbose_name_plural = "Doctor Availabilities"
        unique_together = ('doctor', 'day_of_week', 'start_time', 'end_time')

    def __str__(self):
        day_name = dict(WEEKDAY_CHOICES).get(self.day_of_week)
        return f"{self.doctor} - {day_name}: {self.start_time.strftime('%H:%M')} to {self.end_time.strftime('%H:%M')}"

class Appointment(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='appointments')
    date = models.DateField()
    time_slot = models.TimeField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Scheduled')
    symptoms = models.TextField(blank=True, null=True)
    doctor_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-time_slot']
        unique_together = ('doctor', 'date', 'time_slot')

    def __str__(self):
        return f"{self.patient} with {self.doctor} on {self.date} at {self.time_slot.strftime('%I:%M %p')}"
