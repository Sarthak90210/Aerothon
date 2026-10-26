"""Transmitter channels as the FC reports them, on /aerothon/rc/in.

MAVROS sizes /mavros/rc/in by RC_CHANNELS.chancount. ArduPilot reports a
chancount of 0 when the sticks arrive as RC overrides rather than through its
own receiver input -- an ExpressLRS receiver in MAVLink mode on a TELEM port
(the aircraft, 25 Oct 2026: SERIAL2 MAVLink2 at 460800). The channel values
were live (Mission Planner showed them; channel 5 read 2000 us) while MAVROS
published an empty list, so channel-5 winch drive, the transmitter test and
its takeover switch all saw no transmitter.

This node decodes RC_CHANNELS (#65) from MAVROS's raw FCU stream and
republishes the values as mavros_msgs/RCIn: chancount channels when the FC
gives a count, otherwise the leading channels that carry a value (MAVLink
marks an unused channel 0 or UINT16_MAX). Nothing is inferred: a lost radio
stops the messages, and consumers already treat a stale topic as no input.
"""
import struct

RC_CHANNELS = 65
UNUSED = (0, 0xFFFF)


def decode_rc_channels(payload: bytes):
    """(channels, rssi) from an RC_CHANNELS payload (MAVLink 2 may trim it)."""
    raw = payload.ljust(42, b'\0')
    values = list(struct.unpack_from('<18H', raw, 4))
    count, rssi = raw[40], raw[41]
    if count:
        return values[:min(count, 18)], rssi
    used = 0
    while used < 18 and values[used] not in UNUSED:
        used += 1
    return values[:used], rssi


def main():
    import rclpy
    from mavros_msgs.msg import Mavlink, RCIn
    from rclpy.qos import qos_profile_sensor_data

    rclpy.init()
    node = rclpy.create_node('rc_in_bridge')
    publisher = node.create_publisher(RCIn, '/aerothon/rc/in', qos_profile_sensor_data)

    def on_mavlink(message):
        if message.msgid != RC_CHANNELS:
            return
        payload = b''.join(struct.pack('<Q', word) for word in message.payload64)[:message.len]
        channels, rssi = decode_rc_channels(payload)
        out = RCIn()
        out.header.stamp = node.get_clock().now().to_msg()
        out.rssi = rssi
        out.channels = channels
        publisher.publish(out)

    node.create_subscription(Mavlink, '/uas1/mavlink_source', on_mavlink, qos_profile_sensor_data)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
