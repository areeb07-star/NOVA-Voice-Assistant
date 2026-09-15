from app import get_connection, generate_embedding
from pgvector import Vector


def migrate_note_embeddings():

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Find notes that don't have embeddings yet
        cur.execute("""
            SELECT id, text
            FROM notes
            WHERE embedding IS NULL
            ORDER BY id
        """)

        notes = cur.fetchall()

        total = len(notes)

        if total == 0:
            print("No notes need migration.")
            return

        print(f"Found {total} notes without embeddings.")
        print("Starting migration...\n")

        successful = 0
        failed = 0

        for note_id, text in notes:

            try:
                print(f"Processing note {note_id}...")

                # Generate document embedding
                embedding_values = generate_embedding(
                    text,
                    task_type="RETRIEVAL_DOCUMENT"
                )

                # Save embedding
                cur.execute("""
                    UPDATE notes
                    SET embedding = %s
                    WHERE id = %s
                """, (
                    Vector(embedding_values),
                    note_id
                ))

                conn.commit()

                successful += 1

                print(
                    f"✓ Note {note_id} migrated successfully."
                )

            except Exception as e:

                conn.rollback()

                failed += 1

                print(
                    f"✗ Note {note_id} failed: {e}"
                )

        print("\n" + "=" * 50)
        print("MIGRATION COMPLETE")
        print("=" * 50)
        print(f"Total notes : {total}")
        print(f"Successful  : {successful}")
        print(f"Failed      : {failed}")

    finally:

        cur.close()
        conn.close()


if __name__ == "__main__":
    migrate_note_embeddings()