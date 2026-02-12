(reference_metrics)=

# Metrics

The [BIRD exporter](https://github.com/czerwonk/bird_exporter) inside the WireGuard gateway charm provides the following metrics:

* **bird_ospf_interface_count**: Number of interfaces in the area
* **bird_ospf_neighbor_adjacent_count**: Number of adjacent neighbors in the area
* **bird_ospf_neighbor_count**: Number of neighbors in the area
* **bird_ospf_running**: State of OSPF: 0 = Alone, 1 = Running (Neighbor-Adjacencies established)
* **bird_ospfv3_interface_count**: Number of interfaces in the area
* **bird_ospfv3_neighbor_adjacent_count**: Number of adjacent neighbors in the area
* **bird_ospfv3_neighbor_count**: Number of neighbors in the area
* **bird_ospfv3_running**: State of OSPF: 0 = Alone, 1 = Running (Neighbor-Adjacencies established)
* **bird_protocol_changes_update_export_accept_count**: Number of outgoing updates being accepted
* **bird_protocol_changes_update_export_filter_count**: Number of outgoing updates being filtered
* **bird_protocol_changes_update_export_ignore_count**: Number of outgoing updates being ignored
* **bird_protocol_changes_update_export_receive_count**: Number of sent updates
* **bird_protocol_changes_update_export_reject_count**: Number of outgoing updates being rejected
* **bird_protocol_changes_update_import_accept_count**: Number of incoming updates being accepted
* **bird_protocol_changes_update_import_filter_count**: Number of incoming updates being filtered
* **bird_protocol_changes_update_import_ignore_count**: Number of incoming updates being ignored
* **bird_protocol_changes_update_import_receive_count**: Number of received updates
* **bird_protocol_changes_update_import_reject_count**: Number of incoming updates being rejected
* **bird_protocol_changes_withdraw_export_accept_count**: Number of outgoing withdraws being accepted
* **bird_protocol_changes_withdraw_export_filter_count**: Number of outgoing withdraws being filtered
* **bird_protocol_changes_withdraw_export_ignore_count**: Number of outgoing withdraws being ignored
* **bird_protocol_changes_withdraw_export_receive_count**: Number of outgoing withdraws
* **bird_protocol_changes_withdraw_export_reject_count**: Number of outgoing withdraws being rejected
* **bird_protocol_changes_withdraw_import_accept_count**: Number of incoming withdraws being accepted
* **bird_protocol_changes_withdraw_import_filter_count**: Number of incoming withdraws being filtered
* **bird_protocol_changes_withdraw_import_ignore_count**: Number of incoming withdraws being ignored
* **bird_protocol_changes_withdraw_import_receive_count**: Number of received withdraws
* **bird_protocol_changes_withdraw_import_reject_count**: Number of incoming withdraws being rejected
* **bird_protocol_prefix_export_count**: Number of exported routes
* **bird_protocol_prefix_filter_count**: Number of filtered routes
* **bird_protocol_prefix_import_count**: Number of imported routes
* **bird_protocol_prefix_preferred_count**: Number of preferred routes
* **bird_protocol_up**: Protocol is up
* **bird_protocol_uptime**: Uptime of the protocol in seconds
* **bird_socket_query_success**: Result of querying bird socket: 0 = failed, 1 = succeeded
