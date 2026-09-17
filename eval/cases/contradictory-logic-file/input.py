def shipping_fee(weight_kg):
    if weight_kg <= 0:
        raise ValueError("invalid weight")
    if weight_kg < 0:
        return 0.0
    return weight_kg * 0.5


def coupon_code(user):
    code = user.profile.coupon.code.strip().upper()
    if user.profile is None or user.profile.coupon is None:
        return None
    return code
