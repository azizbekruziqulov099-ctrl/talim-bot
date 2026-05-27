for row in rows:

    subject = str(
        row[1]
    ).upper()

    quarter = f"Q{row[2]}"

    bob = str(
        row[3]
    ).strip()

    bolim = str(
        row[4]
    ).strip()

    mavzu = str(
        row[5]
    ).strip()

    kichik = str(
        row[6]
    ).strip()

    if bob not in bob_map:

        bob_map[bob] = (
            len(bob_map) + 1
        )

    bob_no = bob_map[bob]

    bolim_key = (
        f"{bob}|{bolim}"
    )

    if bolim_key not in bolim_map:

        bolim_map[
            bolim_key
        ] = (
            len([
                x
                for x in bolim_map
                if x.startswith(
                    f"{bob}|"
                )
            ]) + 1
        )

    bolim_no = bolim_map[
        bolim_key
    ]

    mavzu_key = (
        f"{bolim_key}|{mavzu}"
    )

    if mavzu_key not in mavzu_map:

        mavzu_map[
            mavzu_key
        ] = (
            len([
                x
                for x in mavzu_map
                if x.startswith(
                    f"{bolim_key}|"
                )
            ]) + 1
        )

    mavzu_no = mavzu_map[
        mavzu_key
    ]

    kichik_key = (
        f"{mavzu_key}|{kichik}"
    )

    if kichik_key not in kichik_map:

        kichik_map[
            kichik_key
        ] = (
            len([
                x
                for x in kichik_map
                if x.startswith(
                    f"{mavzu_key}|"
                )
            ]) + 1
        )

    kichik_no = kichik_map[
        kichik_key
    ]

    topic_code = (
        f"{subject}-"
        f"{quarter}-"
        f"B{bob_no:02d}-"
        f"BL{bolim_no:02d}-"
        f"M{mavzu_no:02d}-"
        f"S{kichik_no:03d}"
    )

    grade = normalize_text(
        row[0]
    ).replace(
        "sinf",
        ""
    ).strip()

    quarter = normalize_text(
        row[2]
    ).replace(
        "chorak",
        ""
    ).strip()

    cur.execute(
        """
        INSERT INTO dts_tree (
            topic_code,
            grade,
            quarter,
            subject,
            track,
            bob_code,
            bolim_code,
            mavzu_code,
            kichik_mavzu_code,
            bob_name,
            bolim_name,
            mavzu_name,
            kichik_mavzu_name
        )
        VALUES (
            %s,%s,%s,%s,
            'DTS',
            %s,%s,%s,%s,
            %s,%s,%s,%s
        )
        ON CONFLICT (topic_code)
        DO NOTHING
        """,
        (
            topic_code,
            grade,
            quarter,
            subject,
            f"B{bob_no:02d}",
            f"BL{bolim_no:02d}",
            f"M{mavzu_no:02d}",
            f"S{kichik_no:03d}",
            bob,
            bolim,
            mavzu,
            kichik
        )
    )

    added += 1


conn.commit()

cur.execute("""
SELECT COUNT(*)
FROM dts_tree
""")

total_topics = cur.fetchone()[0]

cur.close()
conn.close()

await call.message.answer(
    f"✅ DTS import tugadi\n\n"
    f"📥 Qo'shildi: {added}\n"
    f"📚 Jami mavzular: {total_topics}"
)

dts_import_cache.pop(
    user_id,
    None
)
