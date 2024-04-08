def get_primary_domain(domain_name: str):
    """Extract the primary domain from a domain name."""
    parts = domain_name.split(".")

    if len(parts) >= 2:
        return ".".join(parts[-2:])
    else:
        raise ValueError(f"Invalid domain name: {domain_name}")
