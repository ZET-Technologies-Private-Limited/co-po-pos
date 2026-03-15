import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.infrastructure.redis_client import set_json, close_redis_client

async def main():
    payload = {
        'items': [
            {'code': '2025-26', 'is_active': True, 'is_locked': False, 'read_only': False, 'lock_date': None},
            {'code': '2024-25', 'is_active': False, 'is_locked': True, 'read_only': True, 'lock_date': '2025-06-30T00:00:00Z'},
            {'code': '2023-24', 'is_active': False, 'is_locked': True, 'read_only': True, 'lock_date': '2024-06-30T00:00:00Z'},
            {'code': '2022-23', 'is_active': False, 'is_locked': True, 'read_only': True, 'lock_date': '2023-06-30T00:00:00Z'},
        ]
    }
    await set_json('faculty:ay_configs', payload)
    
    await close_redis_client()
    
    print('Academic years seeded into Redis.')

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
