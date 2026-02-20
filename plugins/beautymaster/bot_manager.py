import asyncio

# ... existing code ...

async def notify_method_1():
    try:
        await asyncio.wait_for(telegram_api_call(), timeout=10)
    except asyncio.TimeoutError:
        # Handle the timeout situation
        print('Timeout occurred in notify_method_1')
    except Exception as e:
        # Handle other exceptions
        print(f'An error occurred: {e}')

async def notify_method_2():
    try:
        await asyncio.wait_for(telegram_api_call(), timeout=10)
    except asyncio.TimeoutError:
        # Handle the timeout situation
        print('Timeout occurred in notify_method_2')
    except Exception as e:
        # Handle other exceptions
        print(f'An error occurred: {e}')

# Add similar try-except structure for all other notify methods.

# ... existing code ...
