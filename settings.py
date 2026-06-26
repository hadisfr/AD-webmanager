from decouple import config


def get_ldap_server(ldap_domain: str):
    import dns.resolver
    import dns.rdatatype
    import operator

    record = "_ldap._tcp.%s." % ldap_domain
    answers = []

    # Query the DNS
    try:
        for answer in dns.resolver.query(record, dns.rdatatype.SRV):
            address = (answer.target.to_text()[:-1], answer.port)
            answers.append((address, answer.priority, answer.weight))
    except Exception:
        # Ignore exceptions, an empty list will trigger an exception anyway
        pass

    # Order by priority and weight
    servers = [entry[0][0] for entry in sorted(answers,
                                               key=operator.itemgetter(1, 2))]
    if not servers:
        raise Exception("No LDAP server in domain '%s'." % ldap_domain)

    if len(servers) == 1:
        return servers[0]
    else:
        return servers


class Settings:
    LDAP_DOMAIN = config("LDAP_DOMAIN")
    LDAP_SERVER = config("LDAP_SERVER", get_ldap_server(LDAP_DOMAIN))
    LDAP_DN = config("LDAP_DN", "DC=%s" % ",DC=".join(LDAP_DOMAIN.split(".")))
    SEARCH_DN = config("SEARCH_DN")
    SICCIP_AWARE = config("SICCIP_AWARE", False)
    ADMIN_GROUP = config("ADMIN_GROUP", "Domain Admins")

    TIMEZONE = config("TIMEZONE", "UTC")
    USE_LOGGING = config("USE_LOGGING", True)
    DEBUG = config("DEBUG", False)

    TREE_BLACKLIST = [
        "CN=ForeignSecurityPrincipals", "OU=sudoers", "CN=Builtin",
        "CN=Infrastructure", "CN=LostAndFound", "CN=Managed Service Accounts",
        "CN=NTDS Quotas", "CN=Program Data", "CN=System",
        "OU=Domain Controllers", "CN=Guest", "CN=krbtgt"
    ]
    SEARCH_ATTRS = [('sAMAccountName', 'Username'), ('givenName', 'Name')]
    USER_ATTRIBUTES = [
        ["jpegPhoto", "Photo"],
    ]
    TREE_ATTRIBUTES = [
        ['mail', "Email"], ['__type', "Type"], ['active', "Status"]
    ]
