def apply_credit(account_id, amount):
    """Add promotional credit to an account balance."""
    account = Account.objects.get(id=account_id)
    new_balance = account.balance + amount
    Account.objects.filter(id=account_id).update(balance=new_balance)
    return new_balance
