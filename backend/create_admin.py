import getpass

from pwdlib import PasswordHash

from app.database import SessionLocal
from app.models import Admin


password_hash = PasswordHash.recommended()


def create_admin():

    db = SessionLocal()

    try:

        print("\n==============================")
        print("      CREATE ADMIN ACCOUNT")
        print("==============================\n")

        full_name = input(
            "Admin full name: "
        ).strip()

        email = input(
            "Admin email: "
        ).strip().lower()

        if not full_name:

            print(
                "❌ Full name cannot be empty."
            )

            return

        if not email:

            print(
                "❌ Email cannot be empty."
            )

            return

        existing_admin = (
            db.query(Admin)
            .filter(
                Admin.email == email
            )
            .first()
        )

        if existing_admin:

            print(
                "❌ Admin with this email already exists."
            )

            return

        password = getpass.getpass(
            "Admin password: "
        )

        if not password:

            print(
                "❌ Password cannot be empty."
            )

            return

        confirm_password = getpass.getpass(
            "Confirm password: "
        )

        if password != confirm_password:

            print(
                "❌ Passwords do not match."
            )

            return

        hashed_password = (
            password_hash.hash(password)
        )

        admin = Admin(

            full_name=full_name,

            email=email,

            password_hash=hashed_password,

            is_active=True
        )

        db.add(admin)

        db.commit()

        db.refresh(admin)

        print(
            "\n✅ Admin account created successfully!"
        )

        print(
            f"Admin ID: {admin.id}"
        )

        print(
            f"Name: {admin.full_name}"
        )

        print(
            f"Email: {admin.email}"
        )

    except Exception as e:

        db.rollback()

        print(
            "\n❌ Failed to create admin."
        )

        print(
            f"Error: {e}"
        )

    finally:

        db.close()


if __name__ == "__main__":

    create_admin()