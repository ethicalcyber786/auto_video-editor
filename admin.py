import os
from app import db, User, app

def admin_panel():
    # Flask context ke andar kaam karna zaroori hai
    with app.app_context():
        print("\n" + "═"*45)
        print("      🛡️  MLS STRONG - ADMIN CONTROL  🛡️")
        print("═"*45)

        # 1. User mangna
        target_user = input("\n[?] Kounse User ke credits change karne hain? (Username): ").strip()
        user = User.query.filter_by(username=target_user).first()

        if not user:
            print(f"\n[!] ERROR: '{target_user}' naam ka koi user nahi mila!")
            return

        # 2. Current Status dikhana
        print(f"\n┌── USER DATA ─────────────────")
        print(f"│ > Username : {user.username}")
        print(f"│ > Current Credits: {user.credits}")
        print(f"└──────────────────────────────")

        print("\n[1] ADD Credits (Subscription ke liye)")
        print("[2] CUT Credits (Refund ya Cancel ke liye)")
        print("[3] EXIT")

        choice = input("\n[?] Select Option (1-3): ").strip()

        try:
            if choice == "1":
                amount = int(input("\n[+] Kitne credits DENE hain?: "))
                user.credits += amount
                db.session.commit()
                print(f"\n✅ SUCCESS: {amount} Credits add ho gaye! Naye credits: {user.credits}")

            elif choice == "2":
                amount = int(input("\n[-] Kitne credits KAATNE (CUT) hain?: "))
                if amount > user.credits:
                    print("\n[!] Warning: User ke paas itne credits nahi hain, balance 0 ho jayega.")
                
                user.credits -= amount
                db.session.commit()
                print(f"\n✅ SUCCESS: {amount} Credits cut ho gaye! Naye credits: {user.credits}")

            elif choice == "3":
                print("\nExiting Admin Tool...")
                return
            
            else:
                print("\n[!] Galat option select kiya!")

        except ValueError:
            print("\n[!] ERROR: Bhai sirf Number (Ginti) likha karo!")
        except Exception as e:
            db.session.rollback()
            print(f"\n[!] System Error: {str(e)}")

if __name__ == "__main__":
    admin_panel()
