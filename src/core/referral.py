from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from src.models.client import ClientRequest, ClientRequestService, Client
from src.models.barber import BarberService, Barber
from src.models.users import User
from src.models.settings import SystemSetting

async def award_referral_bonus(db: AsyncSession, request_id: int):
    # 1. Get the request with its services and the client
    stmt = (
        select(ClientRequest)
        .where(ClientRequest.id == request_id)
    )
    result = await db.execute(stmt)
    request = result.scalar_one_or_none()
    
    if not request or request.status != "done":
        return

    # 2. Calculate total price
    # Joining ClientRequestService and BarberService to get prices
    price_stmt = (
        select(BarberService.price)
        .join(ClientRequestService, ClientRequestService.barber_service_id == BarberService.id)
        .where(ClientRequestService.client_request_id == request_id)
    )
    price_result = await db.execute(price_stmt)
    prices = price_result.scalars().all()
    total_price = sum(prices) if prices else 0

    if total_price <= 0:
        return

    # 3. Get referral percentage from settings
    setting_stmt = select(SystemSetting.value).where(SystemSetting.key == "referral_percentage")
    setting_result = await db.execute(setting_stmt)
    percentage_str = setting_result.scalar_one_or_none()
    percentage = float(percentage_str) if percentage_str else 10.0 # Default 10%

    reward = int(total_price * (percentage / 100))

    if reward <= 0:
        return

    # 4. Find the referrer
    # First get the user associated with this client
    user_stmt = select(User).join(Client, Client.user_id == User.id).where(Client.id == request.client_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if user and user.referred_by_id:
        # Update referrer's balance
        await db.execute(
            update(User)
            .where(User.id == user.referred_by_id)
            .values(balance=User.balance + reward)
        )
    
    # 5. Handle Loyalty Program (Every 10th customer)
    barber_stmt = select(Barber).where(Barber.id == request.barber_id)
    barber_result = await db.execute(barber_stmt)
    barber = barber_result.scalar_one_or_none()
    
    if barber:
        # Increment counter
        new_total = (barber.total_clients_served or 0) + 1
        await db.execute(
            update(Barber)
            .where(Barber.id == barber.id)
            .values(total_clients_served=new_total)
        )
        
        # Check for 10th customer
        if new_total % 10 == 0 and barber.loyalty_reward_type != 'none':
            loyalty_discount = 0
            if barber.loyalty_reward_type == 'free':
                loyalty_discount = total_price
            elif barber.loyalty_reward_type == 'percentage':
                loyalty_discount = int(total_price * (barber.loyalty_reward_value / 100))
            
            if loyalty_discount > 0:
                await db.execute(
                    update(ClientRequest)
                    .where(ClientRequest.id == request_id)
                    .values(discount=(ClientRequest.discount or 0) + loyalty_discount)
                )

    await db.commit()
