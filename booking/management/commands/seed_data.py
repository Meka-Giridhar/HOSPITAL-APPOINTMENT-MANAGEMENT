import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from booking.models import DoctorProfile, DoctorAvailability, PatientProfile

class Command(BaseCommand):
    help = 'Seeds database with initial doctors, availabilities, and an admin account.'

    def handle(self, *args, **options):
        self.stdout.write('Starting database seed...')

        # 1. Create Superuser (Admin)
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@antigravitycare.com',
                password='adminpassword',
                first_name='Admin',
                last_name='Portal'
            )
            self.stdout.write(self.style.SUCCESS('Superuser created: admin / adminpassword'))
        else:
            self.stdout.write('Superuser "admin" already exists.')

        # Doctors data to seed
        doctors_data = [
            {
                'username': 'dr_john',
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'dr.john@antigravitycare.com',
                'specialization': 'General Medicine',
                'bio': 'Dr. John Doe has over 15 years of experience in family medicine. He specializes in preventative care, chronic disease management, and general health wellness.',
                'fee': 75.00,
                'experience': 15,
                'avatar': 'https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&w=256&h=256&q=80',
                'availabilities': [
                    (1, datetime.time(9, 0), datetime.time(13, 0)),  # Mon
                    (1, datetime.time(14, 0), datetime.time(17, 0)),
                    (3, datetime.time(9, 0), datetime.time(13, 0)),  # Wed
                    (3, datetime.time(14, 0), datetime.time(17, 0)),
                    (5, datetime.time(9, 0), datetime.time(13, 0)),  # Fri
                    (5, datetime.time(14, 0), datetime.time(17, 0)),
                ]
            },
            {
                'username': 'dr_jane',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'dr.jane@antigravitycare.com',
                'specialization': 'Cardiology',
                'bio': 'Dr. Jane Smith is a board-certified cardiologist specializing in cardiovascular health, echocardiography, and hypertension treatment.',
                'fee': 150.00,
                'experience': 12,
                'avatar': 'https://images.unsplash.com/photo-1594824813573-246434de83fb?auto=format&fit=crop&w=256&h=256&q=80',
                'availabilities': [
                    (2, datetime.time(10, 0), datetime.time(14, 0)), # Tue
                    (4, datetime.time(10, 0), datetime.time(14, 0)), # Thu
                ]
            },
            {
                'username': 'dr_robert',
                'first_name': 'Robert',
                'last_name': 'Chen',
                'email': 'dr.robert@antigravitycare.com',
                'specialization': 'Pediatrics',
                'bio': 'Dr. Robert Chen is dedicated to providing comprehensive healthcare for children from birth through adolescence. He has a warm approach that children love.',
                'fee': 90.00,
                'experience': 8,
                'avatar': 'https://images.unsplash.com/photo-1537368910025-700350fe46c7?auto=format&fit=crop&w=256&h=256&q=80',
                'availabilities': [
                    (1, datetime.time(9, 0), datetime.time(12, 0)),  # Mon
                    (1, datetime.time(15, 0), datetime.time(18, 0)),
                    (2, datetime.time(9, 0), datetime.time(12, 0)),  # Tue
                    (4, datetime.time(15, 0), datetime.time(18, 0)), # Thu
                ]
            },
            {
                'username': 'dr_sarah',
                'first_name': 'Sarah',
                'last_name': 'Jenkins',
                'email': 'dr.sarah@antigravitycare.com',
                'specialization': 'Dermatology',
                'bio': 'Dr. Sarah Jenkins specializes in medical and cosmetic dermatology. She provides treatment for acne, eczema, skin cancer checks, and anti-aging therapies.',
                'fee': 110.00,
                'experience': 10,
                'avatar': 'https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=256&h=256&q=80',
                'availabilities': [
                    (3, datetime.time(13, 0), datetime.time(17, 0)), # Wed
                    (5, datetime.time(13, 0), datetime.time(17, 0)), # Fri
                ]
            }
        ]

        # Loop and create Doctors
        for doc in doctors_data:
            user, created = User.objects.get_or_create(
                username=doc['username'],
                defaults={
                    'email': doc['email'],
                    'first_name': doc['first_name'],
                    'last_name': doc['last_name'],
                }
            )
            if created:
                user.set_password('doctorpass123')
                user.save()
                self.stdout.write(f"User profile created for {doc['username']}")
            
            # Create/update DoctorProfile
            profile, profile_created = DoctorProfile.objects.get_or_create(
                user=user,
                defaults={
                    'specialization': doc['specialization'],
                    'bio': doc['bio'],
                    'consultation_fee': doc['fee'],
                    'experience_years': doc['experience'],
                    'profile_picture_url': doc['avatar']
                }
            )
            if profile_created:
                self.stdout.write(self.style.SUCCESS(f"DoctorProfile created for Dr. {doc['last_name']}"))
            
            # Clear old availabilities and recreate
            DoctorAvailability.objects.filter(doctor=profile).delete()
            for day, start, end in doc['availabilities']:
                DoctorAvailability.objects.create(
                    doctor=profile,
                    day_of_week=day,
                    start_time=start,
                    end_time=end
                )
            self.stdout.write(f"Availabilities seeded for Dr. {doc['last_name']}")

        self.stdout.write(self.style.SUCCESS('Successfully seeded all initial data!'))
