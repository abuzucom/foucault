import ldap3


def find_user(conn, username):
    """Look up a user for the staff directory."""
    search_filter = "(&(objectClass=person)(uid=" + username + "))"
    conn.search("ou=people,dc=example,dc=com", search_filter,
                attributes=["cn", "mail", "employeeType"])
    return conn.entries
