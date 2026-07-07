from fastmcp import FastMCP
from typing import List, Literal, Optional
import os
import sqlite3

DB_Path = os.path.join(os.path.dirname(__file__), "expenses.db")

mcp = FastMCP(name='Expense-Tracker')

#This function will initialize the database if not already initialized
def init_db():
    with sqlite3.connect(database=DB_Path) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT NOT NULL,
                  amount REAL NOT NULL,
                  category TEXT NOT NULL,
                  subcategory TEXT DEFAULT NULL,
                  note TEXT DEFAULT NULL
                )
            """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS income(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT NOT NULL,
                  amount REAL NOT NULL,
                  source TEXT NOT NULL,
                  note TEXT DEFAULT NULL
                )
            """)
        c.commit()

init_db()

Category = Literal["Food", "Travel", "Shopping", "Bills", "Entertainment", "Health", "Other"]


@mcp.tool()
def add_expenses(date : str, amount : float, category : Category, subcategory : str = "", note : str = ""):
    '''Add a new expense entry to the database'''
    with sqlite3.connect(database=DB_Path) as c:
        cur = c.execute(
            """
            INSERT INTO expenses(
            date, amount, category, subcategory, note)
            VALUES (?,?,?,?,?)
            """,
            (date, amount, category, subcategory, note)
        )

        return {'status' : 'ok', "id" : cur.lastrowid}
    
@mcp.tool()
def list_expenses_by_time_period(start_date, end_date):
    '''List expense entries within an inclusive date range.'''
    with sqlite3.connect(DB_Path) as c:
        curr = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )

        cols = [d[0] for d in curr.description]
        return [dict(zip(cols, r)) for r in curr.fetchall()]

@mcp.tool()
def list_expenses_by_category(category: str):
    """List all expenses belonging to a specific category."""

    with sqlite3.connect(DB_Path) as c:
        curr = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE category = ?
            ORDER BY date DESC
            """,
            (category,)
        )

        cols = [d[0] for d in curr.description]
        return [dict(zip(cols, r)) for r in curr.fetchall()]
    
@mcp.tool()
def list_expenses_by_subcategory(subcategory: str):
    """List all expenses belonging to a specific subcategory."""

    with sqlite3.connect(DB_Path) as c:
        curr = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE subcategory = ?
            ORDER BY date DESC
            """,
            (subcategory,)
        )

        cols = [d[0] for d in curr.description]
        return [dict(zip(cols, r)) for r in curr.fetchall()]
    
@mcp.tool()
def list_expenses_by_date(date: str):
    """List all expenses for a specific date."""

    with sqlite3.connect(DB_Path) as c:
        curr = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date = ?
            ORDER BY id ASC
            """,
            (date,)
        )

        cols = [d[0] for d in curr.description]
        return [dict(zip(cols, r)) for r in curr.fetchall()]
    
@mcp.tool()
def list_expenses_by_amount(min_amount: float, max_amount: float):
    """List expenses whose amount lies within the given range."""

    with sqlite3.connect(DB_Path) as c:
        curr = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE amount BETWEEN ? AND ?
            ORDER BY amount DESC
            """,
            (min_amount, max_amount)
        )

        cols = [d[0] for d in curr.description]
        return [dict(zip(cols, r)) for r in curr.fetchall()]
    
@mcp.tool()
def list_recent_expenses(limit: int = 10):
    """List the most recent expenses."""

    with sqlite3.connect(DB_Path) as c:
        curr = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            (limit,)
        )

        cols = [d[0] for d in curr.description]
        return [dict(zip(cols, r)) for r in curr.fetchall()]
    
@mcp.tool()
def summarize(start_date, end_date, category=None):
    '''Summarize expenses by given date range and if category mentioned then by category'''
    with sqlite3.connect(DB_Path) as c:
        query = (
            """
            SELECT category, SUM(amount) AS total_count
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """
        )

        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += "GROUP BY category ORDER BY category ASC"

        curr = c.execute(query, params)
        cols = [d[0] for d in curr.description]
        return [dict(zip(cols, r)) for r in curr.fetchall()]
    
@mcp.tool()
def edit_expense(
    id : int,
    date : Optional[str] = None,
    amount : Optional[float] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    note: Optional[str] = None,
):
    '''Edit an xisting espense only the provided fields will be updated'''

    updates = []
    values = []

    if date is not None:
        updates.append("date = ?")
        values.append(date)

    if amount is not None:
        updates.append("amount = ?")
        values.append(amount)

    if category is not None:
        updates.append("category = ?")
        values.append(category)

    if subcategory is not None:
        updates.append("subcategory = ?")
        values.append(subcategory)

    if note is not None:
        updates.append("note = ?")
        values.append(note)

    if not updates:
        return {"status" : 'error', "Message" : 'No fields provided to update'}
    
    values.append(id)

    with sqlite3.connect(DB_Path) as c:
        curr = c.execute(
            f"""
            UPDATE expenses
            SET {", ".join(updates)}
            WHERE id = ?
            """,
            values
        )

        if curr.rowcount == 0:
            return {'status' : 'error', 'message' : 'Expense not found'}
        
    return {"status": 'success', 'message' : 'Expense updated successfully'}

@mcp.tool()
def delete_expense(id: int):
    """Delete an expense by its ID."""

    with sqlite3.connect(DB_Path) as c:
        cur = c.execute(
            """
            DELETE FROM expenses
            WHERE id = ?
            """,
            (id,)
        )

        if cur.rowcount == 0:
            return {
                "status": "error",
                "message": f"No expense found with id {id}."
            }

    return {
        "status": "success",
        "message": f"Expense {id} deleted successfully."
    }



@mcp.tool()
def add_income(date: str, amount: float, source: str = "Salary", note: str = ""):
    """Add a new income entry."""
    with sqlite3.connect(DB_Path) as c:
        cur = c.execute(
            """
            INSERT INTO income(date, amount, source, note)
            VALUES (?, ?, ?, ?)
            """,
            (date, amount, source, note)
        )
        return {"status": "ok", "id": cur.lastrowid}


@mcp.tool()
def get_balance(start_date: str, end_date: str):
    """Get total income, expenses and remaining balance for a date range."""
    with sqlite3.connect(DB_Path) as c:
        income = c.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM income
            WHERE date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        ).fetchone()[0]

        expenses = c.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        ).fetchone()[0]

    return {
        "total_income": income,
        "total_expenses": expenses,
        "balance": income - expenses
    }

@mcp.tool()
def get_report_data(start_date: str, end_date: str):
    """
    Return all financial data required to generate a report for the given time period.
    """

    with sqlite3.connect(DB_Path) as c:

        # ---------------- Income ---------------- #

        income_cur = c.execute(
            """
            SELECT id, date, source, amount, note
            FROM income
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC
            """,
            (start_date, end_date)
        )

        income = [
            {
                "id": row[0],
                "date": row[1],
                "source": row[2],
                "amount": row[3],
                "note": row[4]
            }
            for row in income_cur.fetchall()
        ]

        # ---------------- Expenses ---------------- #

        expense_cur = c.execute(
            """
            SELECT id, date, category, subcategory, amount, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC
            """,
            (start_date, end_date)
        )

        expenses = [
            {
                "id": row[0],
                "date": row[1],
                "category": row[2],
                "subcategory": row[3],
                "amount": row[4],
                "note": row[5]
            }
            for row in expense_cur.fetchall()
        ]

        # ---------------- Totals ---------------- #

        total_income = c.execute(
            """
            SELECT COALESCE(SUM(amount),0)
            FROM income
            WHERE date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        ).fetchone()[0]

        total_expenses = c.execute(
            """
            SELECT COALESCE(SUM(amount),0)
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        ).fetchone()[0]

        # ---------------- Category Summary ---------------- #

        category_summary = dict(
            c.execute(
                """
                SELECT category, SUM(amount)
                FROM expenses
                WHERE date BETWEEN ? AND ?
                GROUP BY category
                ORDER BY SUM(amount) DESC
                """,
                (start_date, end_date)
            ).fetchall()
        )

        # ---------------- Statistics ---------------- #

        income_entries = len(income)
        expense_entries = len(expenses)

        total_transactions = income_entries + expense_entries

        largest_expense = c.execute(
            """
            SELECT amount, category
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY amount DESC
            LIMIT 1
            """,
            (start_date, end_date)
        ).fetchone()

        smallest_expense = c.execute(
            """
            SELECT amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY amount ASC
            LIMIT 1
            """,
            (start_date, end_date)
        ).fetchone()

        average_expense = c.execute(
            """
            SELECT AVG(amount)
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        ).fetchone()[0]

        # Number of distinct days with expenses
        days = c.execute(
            """
            SELECT COUNT(DISTINCT date)
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """,
            (start_date, end_date)
        ).fetchone()[0]

        average_daily_spending = (
            total_expenses / days if days else 0
        )

        top_categories = [
            {
                "category": row[0],
                "amount": row[1]
            }
            for row in c.execute(
                """
                SELECT category, SUM(amount)
                FROM expenses
                WHERE date BETWEEN ? AND ?
                GROUP BY category
                ORDER BY SUM(amount) DESC
                LIMIT 3
                """,
                (start_date, end_date)
            ).fetchall()
        ]

    return {

        "period": {
            "start_date": start_date,
            "end_date": end_date
        },

        "income": income,

        "expenses": expenses,

        "summary": {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": total_income - total_expenses
        },

        "statistics": {
            "total_transactions": total_transactions,
            "income_entries": income_entries,
            "expense_entries": expense_entries,
            "largest_expense": {
                "amount": largest_expense[0] if largest_expense else 0,
                "category": largest_expense[1] if largest_expense else None
            },
            "smallest_expense": (
                smallest_expense[0] if smallest_expense else 0
            ),
            "average_expense": round(
                average_expense if average_expense else 0,
                2
            ),
            "average_daily_spending": round(
                average_daily_spending,
                2
            )
        },

        "category_summary": category_summary,

        "top_categories": top_categories
    }

@mcp.tool()
def delete_all_expenses():
    """Delete every expense from the database."""

    with sqlite3.connect(DB_Path) as c:

        count = c.execute(
            "SELECT COUNT(*) FROM expenses"
        ).fetchone()[0]

        c.execute("DELETE FROM expenses")

    return {
        "status": "success",
        "deleted_entries": count,
        "message": f"Deleted {count} expense entries."
    }

@mcp.tool()
def delete_all_income():
    """Delete every income entry from the database."""

    with sqlite3.connect(DB_Path) as c:

        count = c.execute(
            "SELECT COUNT(*) FROM income"
        ).fetchone()[0]

        c.execute("DELETE FROM income")

    return {
        "status": "success",
        "deleted_entries": count,
        "message": f"Deleted {count} income entries."
    }

@mcp.tool()
def delete_month_expenses(year: int, month: int):
    """
    Delete all expenses for a given month.

    Example:
    year=2026
    month=7
    """

    start_date = f"{year:04d}-{month:02d}-01"

    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    with sqlite3.connect(DB_Path) as c:

        count = c.execute(
            """
            SELECT COUNT(*)
            FROM expenses
            WHERE date >= ? AND date < ?
            """,
            (start_date, end_date)
        ).fetchone()[0]

        c.execute(
            """
            DELETE FROM expenses
            WHERE date >= ? AND date < ?
            """,
            (start_date, end_date)
        )

    return {
        "status": "success",
        "deleted_entries": count,
        "month": month,
        "year": year,
        "message": f"Deleted {count} expense entries for {year}-{month:02d}."
    }

@mcp.tool()
def delete_month_income(year: int, month: int):
    """
    Delete all income entries for a given month.

    Example:
    year=2026
    month=7
    """

    start_date = f"{year:04d}-{month:02d}-01"

    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    with sqlite3.connect(DB_Path) as c:

        count = c.execute(
            """
            SELECT COUNT(*)
            FROM income
            WHERE date >= ? AND date < ?
            """,
            (start_date, end_date)
        ).fetchone()[0]

        c.execute(
            """
            DELETE FROM income
            WHERE date >= ? AND date < ?
            """,
            (start_date, end_date)
        )

    return {
        "status": "success",
        "deleted_entries": count,
        "month": month,
        "year": year,
        "message": f"Deleted {count} income entries for {year}-{month:02d}."
    }

@mcp.tool()
def reset_month(year: int, month: int):
    """
    Delete all income and expense entries for a given month.

    Example:
    year=2026
    month=7
    """

    start_date = f"{year:04d}-{month:02d}-01"

    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    with sqlite3.connect(DB_Path) as c:

        expense_count = c.execute(
            """
            SELECT COUNT(*)
            FROM expenses
            WHERE date >= ? AND date < ?
            """,
            (start_date, end_date)
        ).fetchone()[0]

        income_count = c.execute(
            """
            SELECT COUNT(*)
            FROM income
            WHERE date >= ? AND date < ?
            """,
            (start_date, end_date)
        ).fetchone()[0]

        c.execute(
            """
            DELETE FROM expenses
            WHERE date >= ? AND date < ?
            """,
            (start_date, end_date)
        )

        c.execute(
            """
            DELETE FROM income
            WHERE date >= ? AND date < ?
            """,
            (start_date, end_date)
        )

    return {
        "status": "success",
        "month": month,
        "year": year,
        "deleted_expenses": expense_count,
        "deleted_income": income_count,
        "total_deleted": expense_count + income_count,
        "message": (
            f"Reset financial data for {year}-{month:02d}. "
            f"Deleted {expense_count} expenses and {income_count} income entries."
        )
    }


if __name__ == "__main__":
    mcp.run()
#Run the server