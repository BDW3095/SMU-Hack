import streamlit as st

ROOM_TYPES = [
    "Living Room",
    "Bedroom",
    "Home Office",
    "Dining Room",
    "Bathroom",
    "Study Room",
]

MUST_HAVE_PLACEHOLDERS = [
    "e.g. A large comfy sofa that fits 4 people",
    "e.g. Warm ambient lighting near the reading corner",
    "e.g. Open shelving for books and plants",
]


class ContextForm:
    def render(self) -> dict | None:
        """Render the context form. Returns dict on valid submit, None otherwise."""
        st.subheader("Tell us about your room")

        room_type = st.selectbox("Room type", ROOM_TYPES)

        st.markdown("**What are your top 3 must-haves?** *(max 80 characters each)*")
        must_haves = []
        for i, placeholder in enumerate(MUST_HAVE_PLACEHOLDERS):
            val = st.text_input(
                f"Must-have {i + 1}",
                max_chars=80,
                placeholder=placeholder,
                key=f"must_have_{i}",
            )
            must_haves.append(val.strip())

        filled = [m for m in must_haves if m]
        if st.button("✨ Generate My Designs", type="primary", use_container_width=True):
            if not filled:
                st.warning("Please fill in at least one must-have to help us design your room.")
                return None
            return {"room_type": room_type, "must_haves": must_haves}

        return None
