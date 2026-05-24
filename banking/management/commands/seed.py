from django.core.management.base import BaseCommand
from decimal import Decimal
from accounts.models import CustomUser
from banking.models import Rekening, Transaksi, TopUp
from banking.services import buat_rekening_baru, proses_topup
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Seed data awal'

def handle(self, *args, **kwargs):
        if CustomUser.objects.filter(username='supervisor1').exists():
            self.stdout.write('Data sudah ada, skip seed.')
            return
        
        TopUp.objects.all().delete()
        Transaksi.objects.all().delete()
        Rekening.objects.all().delete()
        CustomUser.objects.exclude(is_superuser=True).delete()
        self.stdout.write('Data lama dibersihkan.')

        CustomUser.objects.exclude(is_superuser=True).delete()

        sup = CustomUser.objects.create_user(
            username='supervisor1', password='password123',
            first_name='Budi', last_name='Santoso',
            email='budi@bank.id', role='supervisor',
            no_telp='08111111111',
        )

        teller1 = CustomUser.objects.create_user(
            username='teller1', password='password123',
            first_name='Siti', last_name='Rahayu',
            email='siti@bank.id', role='teller',
            no_telp='08222222222',
        )
        teller2 = CustomUser.objects.create_user(
            username='teller2', password='password123',
            first_name='Ahmad', last_name='Fauzi',
            email='ahmad@bank.id', role='teller',
            no_telp='08333333333',
        )

        nasabah_data = [
            ('nasabah1', 'Dewi',  'Lestari',   'dewi@mail.com',  Decimal('5000000')),
            ('nasabah2', 'Rizky', 'Pratama',   'rizky@mail.com', Decimal('12500000')),
            ('nasabah3', 'Maya',  'Wulandari', 'maya@mail.com',  Decimal('750000')),
            ('nasabah4', 'Fajar', 'Hidayat',   'fajar@mail.com', Decimal('25000000')),
        ]
        nasabah_users = []
        for username, first, last, email, saldo in nasabah_data:
            u = CustomUser.objects.create_user(
                username=username, password='password123',
                first_name=first, last_name=last,
                email=email, role='nasabah',
            )
            rek = buat_rekening_baru(u, saldo_awal=saldo)
            nasabah_users.append((u, rek))

        u1, r1 = nasabah_users[0]
        u2, r2 = nasabah_users[1]
        u3, r3 = nasabah_users[2]
        u4, r4 = nasabah_users[3]

        Transaksi.objects.create(
            rekening_asal=r1, rekening_tujuan=r2,
            jenis='transfer', nominal=Decimal('500000'),
            keterangan='Bayar makan siang', status='approved',
            diproses_oleh=teller1, waktu_diproses=timezone.now() - timedelta(days=2),
        )
        r1.saldo -= Decimal('500000'); r1.save()
        r2.saldo += Decimal('500000'); r2.save()

        Transaksi.objects.create(
            rekening_asal=r4, rekening_tujuan=r1,
            jenis='transfer', nominal=Decimal('15000000'),
            keterangan='Cicilan rumah', status='pending',
        )
        Transaksi.objects.create(
            rekening_asal=r3, rekening_tujuan=r2,
            jenis='transfer', nominal=Decimal('1000000'),
            keterangan='Test transfer', status='rejected',
            diproses_oleh=teller1, waktu_diproses=timezone.now() - timedelta(days=1),
            catatan_staff='Rekening sumber mencurigakan.',
        )
        Transaksi.objects.create(
            rekening_asal=r2, rekening_tujuan=r3,
            jenis='transfer', nominal=Decimal('250000'),
            keterangan='Kiriman bulanan', status='pending',
        )

        top1 = TopUp.objects.create(rekening=r3, nominal=Decimal('2000000'), metode='tunai', status='pending')
        TopUp.objects.create(rekening=r1, nominal=Decimal('500000'), metode='virtual', status='pending')
        proses_topup(top1, teller1, disetujui=True, catatan='Tunai diterima')

        self.stdout.write(self.style.SUCCESS('Seed data berhasil!'))