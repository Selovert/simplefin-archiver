from .update_accounts import update_accounts

if __name__ == "__main__":
    update_accounts.serve(
        name="simplefin-update-accounts",
        tags=["simplefin"],
    )
