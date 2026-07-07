from fastmcp import FastMCP
from typing import List, Literal, Optional
import os
import aiosqlite  

DB_Path = os.path.join(os.path.dirname(__file__), "expenses.db")

mcp = FastMCP(name='Expense-Tracker')

# This function will initialize the database if not already initialized
def init_db():  # Keep as sync for initialization
    import sqlite3
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

# Initialize database synchronously at module load
init_db()

Category = Literal["Food", "Travel", "Shopping", "Bills", "Entertainment", "Health", "Other"]


@mcp.tool()
async def add_expenses(date: str, amount: float, category: Category, subcategory: str = "", note: str = ""): 
    '''Add a new expense entry to the database'''
    try:
        async with aiosqlite.connect(DB_Path) as c:  
            cur = await c.execute(  
                """
                INSERT INTO expenses(
                date, amount, category, subcategory, note)
                VALUES (?,?,?,?,?)
                """,
                (date, amount, category, subcategory, note)
            )
            await c.commit()
            return {'status': 'ok', "id": cur.lastrowid}
    except Exception as e:  
        if "readonly" in str(e).lower():
            return {"status": "error", "message": "Database is in read-only mode. Check file permissions."}
        return {"status": "error", "message": f"Database error: {str(e)}"}


@mcp.tool()
async def list_expenses_by_time_period(start_date, end_date): 
    '''List expense entries within an inclusive date range.'''
    try:
        async with aiosqlite.connect(DB_Path) as c: 
            curr = await c.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY id ASC
                """,
                (start_date, end_date)
            )

            cols = [d[0] for d in curr.description]
            return [dict(zip(cols, r)) for r in await curr.fetchall()] 
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}


@mcp.tool()
async def list_expenses_by_category(category: str): 
    """List all expenses belonging to a specific category."""
    try:
        async with aiosqlite.connect(DB_Path) as c:  
            curr = await c.execute( 
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE category = ?
                ORDER BY date DESC
                """,
                (category,)
            )

            cols = [d[0] for d in curr.description]
            return [dict(zip(cols, r)) for r in await curr.fetchall()]  
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}


@mcp.tool()
async def list_expenses_by_subcategory(subcategory: str):  
    """List all expenses belonging to a specific subcategory."""
    try:
        async with aiosqlite.connect(DB_Path) as c:  
            curr = await c.execute(  
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE subcategory = ?
                ORDER BY date DESC
                """,
                (subcategory,)
            )

            cols = [d[0] for d in curr.description]
            return [dict(zip(cols, r)) for r in await curr.fetchall()]  
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}


@mcp.tool()
async def list_expenses_by_date(date: str):  
    """List all expenses for a specific date."""
    try:
        async with aiosqlite.connect(DB_Path) as c:  
            curr = await c.execute(  
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date = ?
                ORDER BY id ASC
                """,
                (date,)
            )

            cols = [d[0] for d in curr.description]
            return [dict(zip(cols, r)) for r in await curr.fetchall()]  
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}


@mcp.tool()
async def list_expenses_by_amount(min_amount: float, max_amount: float):  
    """List expenses whose amount lies within the given range."""
    try:
        async with aiosqlite.connect(DB_Path) as c:  
            curr = await c.execute(  
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE amount BETWEEN ? AND ?
                ORDER BY amount DESC
                """,
                (min_amount, max_amount)
            )

            cols = [d[0] for d in curr.description]
            return [dict(zip(cols, r)) for r in await curr.fetchall()]  
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}


@mcp.tool()
async def list_recent_expenses(limit: int = 10):  
    """List the most recent expenses."""
    try:
        async with aiosqlite.connect(DB_Path) as c:  
            curr = await c.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                ORDER BY date DESC, id DESC
                LIMIT ?
                """,
                (limit,)
            )

            cols = [d[0] for d in curr.description]
            return [dict(zip(cols, r)) for r in await curr.fetchall()]  
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}


@mcp.tool()
async def summarize(start_date, end_date, category=None): 
    '''Summarize expenses by given date range and if category mentioned then by category'''
    try:
        async with aiosqlite.connect(DB_Path) as c: 
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

            query += " GROUP BY category ORDER BY category ASC"  

            curr = await c.execute(query, params)
            cols = [d[0] for d in curr.description]
            return [dict(zip(cols, r)) for r in await curr.fetchall()] 
    except Exception as e:
        return {"status": "error", "message": f"Error summarizing expenses: {str(e)}"}


@mcp.tool()
async def edit_expense( 
    id: int,
    date: Optional[str] = None,
    amount: Optional[float] = None,
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
        return {"status": 'error', "Message": 'No fields provided to update'}

    values.append(id)

    try:
        async with aiosqlite.connect(DB_Path) as c:  
            curr = await c.execute(  
                f"""
                UPDATE expenses
                SET {", ".join(updates)}
                WHERE id = ?
                """,
                values
            )
            await c.commit() 

            if curr.rowcount == 0:
                return {'status': 'error', 'message': 'Expense not found'}

        return {"status": 'success', 'message': 'Expense updated successfully'}
    except Exception as e:
        return {"status": "error", "message": f"Error editing expense: {str(e)}"}


@mcp.tool()
async def delete_expense(id: int):  
    """Delete an expense by its ID."""
    try:
        async with aiosqlite.connect(DB_Path) as c: 
            cur = await c.execute(  
                """
                DELETE FROM expenses
                WHERE id = ?
                """,
                (id,)
            )
            await c.commit() 

            if cur.rowcount == 0:
                return {
                    "status": "error",
                    "message": f"No expense found with id {id}."
                }

        return {
            "status": "success",
            "message": f"Expense {id} deleted successfully."
        }
    except Exception as e:
        return {"status": "error", "message": f"Error deleting expense: {str(e)}"}


@mcp.tool()
async def add_income(date: str, amount: float, source: str = "Salary", note: str = ""):  
    """Add a new income entry."""
    try:
        async with aiosqlite.connect(DB_Path) as c: 
            cur = await c.execute(  
                """
                INSERT INTO income(date, amount, source, note)
                VALUES (?, ?, ?, ?)
                """,
                (date, amount, source, note)
            )
            await c.commit()  
            return {"status": "ok", "id": cur.lastrowid}
    except Exception as e:
        return {"status": "error", "message": f"Error adding income: {str(e)}"}


@mcp.tool()
async def get_balance(start_date: str, end_date: str): 
    """Get total income, expenses and remaining balance for a date range."""
    try:
        async with aiosqlite.connect(DB_Path) as c:  
            income_cur = await c.execute(  
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM income
                WHERE date BETWEEN ? AND ?
                """,
                (start_date, end_date)
            )
            income = (await income_cur.fetchone())[0] 

            expense_cur = await c.execute(  
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses
                WHERE date BETWEEN ? AND ?
                """,
                (start_date, end_date)
            )
            expenses = (await expense_cur.fetchone())[0]  

        return {
            "total_income": income,
            "total_expenses": expenses,
            "balance": income - expenses
        }
    except Exception as e:
        return {"status": "error", "message": f"Error getting balance: {str(e)}"}


@mcp.tool()
async def get_report_data(start_date: str, end_date: str): 
    """
    Return all financial data required to generate a report for the given time period.
    """
    try:
        async with aiosqlite.connect(DB_Path) as c: 

            # ---------------- Income ---------------- #

            income_cur = await c.execute( 
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
                for row in await income_cur.fetchall()  
            ]

            # ---------------- Expenses ---------------- #

            expense_cur = await c.execute(  
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
                for row in await expense_cur.fetchall()  
            ]

            # ---------------- Totals ---------------- #

            total_income_cur = await c.execute(  
                """
                SELECT COALESCE(SUM(amount),0)
                FROM income
                WHERE date BETWEEN ? AND ?
                """,
                (start_date, end_date)
            )
            total_income = (await total_income_cur.fetchone())[0]  

            total_expenses_cur = await c.execute(  
                """
                SELECT COALESCE(SUM(amount),0)
                FROM expenses
                WHERE date BETWEEN ? AND ?
                """,
                (start_date, end_date)
            )
            total_expenses = (await total_expenses_cur.fetchone())[0]  

            # ---------------- Category Summary ---------------- #

            category_summary_cur = await c.execute( 
                """
                SELECT category, SUM(amount)
                FROM expenses
                WHERE date BETWEEN ? AND ?
                GROUP BY category
                ORDER BY SUM(amount) DESC
                """,
                (start_date, end_date)
            )
            category_summary = dict(await category_summary_cur.fetchall())  

            # ---------------- Statistics ---------------- #

            income_entries = len(income)
            expense_entries = len(expenses)

            total_transactions = income_entries + expense_entries

            largest_expense_cur = await c.execute(  
                """
                SELECT amount, category
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY amount DESC
                LIMIT 1
                """,
                (start_date, end_date)
            )
            largest_expense = await largest_expense_cur.fetchone() 

            smallest_expense_cur = await c.execute( 
                """
                SELECT amount
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY amount ASC
                LIMIT 1
                """,
                (start_date, end_date)
            )
            smallest_expense = await smallest_expense_cur.fetchone()

            average_expense_cur = await c.execute(  
                """
                SELECT AVG(amount)
                FROM expenses
                WHERE date BETWEEN ? AND ?
                """,
                (start_date, end_date)
            )
            average_expense = (await average_expense_cur.fetchone())[0]  

            # Number of distinct days with expenses
            days_cur = await c.execute(  
                """
                SELECT COUNT(DISTINCT date)
                FROM expenses
                WHERE date BETWEEN ? AND ?
                """,
                (start_date, end_date)
            )
            days = (await days_cur.fetchone())[0] 

            average_daily_spending = (
                total_expenses / days if days else 0
            )

            top_categories_cur = await c.execute(  
                """
                SELECT category, SUM(amount)
                FROM expenses
                WHERE date BETWEEN ? AND ?
                GROUP BY category
                ORDER BY SUM(amount) DESC
                LIMIT 3
                """,
                (start_date, end_date)
            )
            top_categories = [
                {
                    "category": row[0],
                    "amount": row[1]
                }
                for row in await top_categories_cur.fetchall() 
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
    except Exception as e:
        return {"status": "error", "message": f"Error generating report: {str(e)}"}


@mcp.tool()
async def delete_all_expenses():  
    """Delete every expense from the database."""
    try:
        async with aiosqlite.connect(DB_Path) as c:

            count_cur = await c.execute("SELECT COUNT(*) FROM expenses")  
            count = (await count_cur.fetchone())[0]  

            await c.execute("DELETE FROM expenses") 
            await c.commit() 

        return {
            "status": "success",
            "deleted_entries": count,
            "message": f"Deleted {count} expense entries."
        }
    except Exception as e:
        return {"status": "error", "message": f"Error deleting expenses: {str(e)}"}


@mcp.tool()
async def delete_all_income():  
    """Delete every income entry from the database."""
    try:
        async with aiosqlite.connect(DB_Path) as c:  

            count_cur = await c.execute("SELECT COUNT(*) FROM income") 
            count = (await count_cur.fetchone())[0]  

            await c.execute("DELETE FROM income") 
            await c.commit()  

        return {
            "status": "success",
            "deleted_entries": count,
            "message": f"Deleted {count} income entries."
        }
    except Exception as e:
        return {"status": "error", "message": f"Error deleting income: {str(e)}"}


@mcp.tool()
async def delete_month_expenses(year: int, month: int):  
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

    try:
        async with aiosqlite.connect(DB_Path) as c: 

            count_cur = await c.execute(  
                """
                SELECT COUNT(*)
                FROM expenses
                WHERE date >= ? AND date < ?
                """,
                (start_date, end_date)
            )
            count = (await count_cur.fetchone())[0]  

            await c.execute(  
                """
                DELETE FROM expenses
                WHERE date >= ? AND date < ?
                """,
                (start_date, end_date)
            )
            await c.commit()  

        return {
            "status": "success",
            "deleted_entries": count,
            "month": month,
            "year": year,
            "message": f"Deleted {count} expense entries for {year}-{month:02d}."
        }
    except Exception as e:
        return {"status": "error", "message": f"Error deleting month expenses: {str(e)}"}


@mcp.tool()
async def delete_month_income(year: int, month: int): 
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

    try:
        async with aiosqlite.connect(DB_Path) as c:  

            count_cur = await c.execute( 
                """
                SELECT COUNT(*)
                FROM income
                WHERE date >= ? AND date < ?
                """,
                (start_date, end_date)
            )
            count = (await count_cur.fetchone())[0]  

            await c.execute(  
                """
                DELETE FROM income
                WHERE date >= ? AND date < ?
                """,
                (start_date, end_date)
            )
            await c.commit()  

        return {
            "status": "success",
            "deleted_entries": count,
            "month": month,
            "year": year,
            "message": f"Deleted {count} income entries for {year}-{month:02d}."
        }
    except Exception as e:
        return {"status": "error", "message": f"Error deleting month income: {str(e)}"}


@mcp.tool()
async def reset_month(year: int, month: int): 
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

    try:
        async with aiosqlite.connect(DB_Path) as c: 

            expense_count_cur = await c.execute(  
                """
                SELECT COUNT(*)
                FROM expenses
                WHERE date >= ? AND date < ?
                """,
                (start_date, end_date)
            )
            expense_count = (await expense_count_cur.fetchone())[0]

            income_count_cur = await c.execute(  
                """
                SELECT COUNT(*)
                FROM income
                WHERE date >= ? AND date < ?
                """,
                (start_date, end_date)
            )
            income_count = (await income_count_cur.fetchone())[0]  

            await c.execute(  
                """
                DELETE FROM expenses
                WHERE date >= ? AND date < ?
                """,
                (start_date, end_date)
            )

            await c.execute(  
                """
                DELETE FROM income
                WHERE date >= ? AND date < ?
                """,
                (start_date, end_date)
            )

            await c.commit() 

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
    except Exception as e:
        return {"status": "error", "message": f"Error resetting month: {str(e)}"}


# Start the server
if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
# Run the server