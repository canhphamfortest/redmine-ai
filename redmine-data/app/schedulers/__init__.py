"""Scheduler Package.

Module này chứa job scheduler service để quản lý và thực thi scheduled jobs:
- JobSchedulerService: Service chính để schedule và quản lý jobs
- Job scheduling: Schedule jobs dựa trên cron expressions
- Job execution: Trigger job execution qua backend API
- Job reloading: Tự động reload jobs khi có thay đổi

Scheduler là lightweight service, chỉ quản lý scheduling, không thực thi jobs trực tiếp.
Jobs được thực thi bởi backend API service.
"""

