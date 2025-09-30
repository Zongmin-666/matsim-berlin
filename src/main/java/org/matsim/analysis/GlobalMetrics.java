package org.matsim.analysis;

import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.events.PersonArrivalEvent;
import org.matsim.api.core.v01.events.PersonDepartureEvent;
import org.matsim.api.core.v01.events.handler.PersonArrivalEventHandler;
import org.matsim.api.core.v01.events.handler.PersonDepartureEventHandler;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.application.CommandSpec;
import org.matsim.application.MATSimAppCommand;
import org.matsim.application.options.InputOptions;
import org.matsim.application.options.OutputOptions;
import org.matsim.core.api.experimental.events.EventsManager;
import org.matsim.core.events.EventsUtils;
import org.matsim.core.events.MatsimEventsReader;
import org.matsim.core.network.NetworkUtils;
import org.matsim.core.network.io.MatsimNetworkReader;
import org.matsim.core.utils.io.IOUtils;
import org.matsim.api.core.v01.events.LinkEnterEvent;
import org.matsim.api.core.v01.events.LinkLeaveEvent;
import org.matsim.api.core.v01.events.handler.LinkEnterEventHandler;
import org.matsim.api.core.v01.events.handler.LinkLeaveEventHandler;
import picocli.CommandLine;
import tech.tablesaw.api.*;

import java.io.PrintWriter;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

@CommandLine.Command(
	name = "global-metrics",
	description = "Compute global traffic metrics (VKT, VHT, AvgSpeed) and hourly trip-time stats."
)
@CommandSpec(
	requireEvents = true,
	requireNetwork = true,
	produces = {"global_metrics.csv", "hourly_trip_time.csv"},
	group = "travelTime"
)
public class GlobalMetrics implements MATSimAppCommand {

	@CommandLine.Mixin
	private InputOptions input = InputOptions.ofCommand(GlobalMetrics.class);

	@CommandLine.Mixin
	private OutputOptions output = OutputOptions.ofCommand(GlobalMetrics.class);

	@CommandLine.Option(names = "--mode", description = "Optional mode filter for trip-time stats (e.g., car).")
	private String modeFilter = null;

	public static void main(String[] args) {
		new GlobalMetrics().execute(args);
	}

	@Override
	public Integer call() throws Exception {

		// 1) Load network
		Network network = NetworkUtils.createNetwork();
		new MatsimNetworkReader(network).readFile(input.getNetworkPath().toString());

		// 2) Prepare handlers
		LinkAgg linkAgg = new LinkAgg(network);
		TripAgg tripAgg = new TripAgg(modeFilter);

		// 3) Read events
		EventsManager mgr = EventsUtils.createEventsManager();
		mgr.addHandler(linkAgg);
		mgr.addHandler(tripAgg);
		new MatsimEventsReader(mgr).readFile(input.getEventsPath().toString());

		// 4) Compute metrics
		double vkt_km = linkAgg.vkt_m / 1000.0;
		double vht_h  = linkAgg.vht_s / 3600.0;
		double avgSpeed_kmh = vht_h > 0 ? (vkt_km / vht_h) : Double.NaN;

		// 5) Write global_metrics.csv
		try (PrintWriter pw = new PrintWriter(IOUtils.getBufferedWriter(output.getPath("global_metrics.csv").toString()))) {
			pw.println("metric,value,unit,notes");
			pw.printf(Locale.ROOT, "VKT,%.6f,km,from LinkEnter/Leave%n", vkt_km);
			pw.printf(Locale.ROOT, "VHT,%.6f,h,from LinkEnter/Leave%n", vht_h);
			pw.printf(Locale.ROOT, "AvgSpeed,%.6f,km/h,VKT/VHT%n", avgSpeed_kmh);
			pw.printf(Locale.ROOT, "TripsAll,%d,count,from PersonDeparture/Arrival%n", tripAgg.tripsAll);
			pw.printf(Locale.ROOT, "AvgTripTimeAll,%.3f,s,all modes%n", tripAgg.avgTripTimeAll());
			if (modeFilter != null && !modeFilter.isBlank()) {
				pw.printf(Locale.ROOT, "Trips[%s],%d,count,mode filtered%n", modeFilter, tripAgg.tripsMode);
				pw.printf(Locale.ROOT, "AvgTripTime[%s],%.3f,s,mode filtered%n", modeFilter, tripAgg.avgTripTimeMode());
			}
		}

		// 6) Hourly trip-time table
		Table hourly = Table.create("hourly_trip_time")
			.addColumns(
				IntColumn.create("hour"),
				DoubleColumn.create("avg_trip_time_all_s"),
				LongColumn.create("trips_all"),
				DoubleColumn.create("avg_trip_time_mode_s"),
				LongColumn.create("trips_mode"),
				StringColumn.create("mode")
			);

		for (int h = 0; h < 24; h++) {
			long nAll  = tripAgg.tripsPerHourAll[h];
			long nMode = tripAgg.tripsPerHourMode[h];
			double avgAll  = nAll  > 0 ? tripAgg.ttSumPerHourAll[h]  / nAll  : Double.NaN;
			double avgMode = nMode > 0 ? tripAgg.ttSumPerHourMode[h] / nMode : Double.NaN;

			hourly.intColumn("hour").append(h);
			hourly.doubleColumn("avg_trip_time_all_s").append(avgAll);
			hourly.longColumn("trips_all").append(nAll);
			hourly.doubleColumn("avg_trip_time_mode_s").append(avgMode);
			hourly.longColumn("trips_mode").append(nMode);
			hourly.stringColumn("mode").append(modeFilter == null ? "" : modeFilter);
		}

		hourly.write().csv(output.getPath("hourly_trip_time.csv").toFile());

		return 0;
	}

	/* ================= Handlers (typed) ================= */

	/** VKT/VHT 聚合：基于 LinkEnter/Leave */
	static class LinkAgg implements LinkEnterEventHandler, LinkLeaveEventHandler {
		private final Network net;
		double vkt_m = 0.0; // meters
		double vht_s = 0.0; // seconds

		private final Map<Id<?>, Double>  vehEnterTime = new HashMap<>();
		private final Map<Id<?>, Id<Link>> vehLink      = new HashMap<>();

		LinkAgg(Network net) { this.net = net; }

		@Override
		public void handleEvent(LinkEnterEvent e) {
			vehEnterTime.put(e.getVehicleId(), e.getTime());
			vehLink.put(e.getVehicleId(), e.getLinkId());
		}

		@Override
		public void handleEvent(LinkLeaveEvent e) {
			Double enter = vehEnterTime.remove(e.getVehicleId());
			Id<Link> lid = vehLink.remove(e.getVehicleId());
			if (enter != null && lid != null) {
				double dt = Math.max(0, e.getTime() - enter);
				vht_s += dt;
				Link l = net.getLinks().get(lid);
				if (l != null) vkt_m += l.getLength();
			}
		}

		@Override public void reset(int iteration) { }
	}

	/** Trip 时间聚合：基于 PersonDeparture/Arrival（含按小时、可选模式过滤） */
	static class TripAgg implements PersonDepartureEventHandler, PersonArrivalEventHandler {
		static class Dep { final double t; final String mode; Dep(double t, String m){ this.t=t; this.mode=m; } }

		private final Map<Id<?>, Dep> depMap = new HashMap<>();
		private final String modeFilter;

		int    tripsAll = 0;  double ttSumAll  = 0.0;
		int    tripsMode = 0; double ttSumMode = 0.0;

		long[]   tripsPerHourAll  = new long[24];
		double[] ttSumPerHourAll  = new double[24];
		long[]   tripsPerHourMode = new long[24];
		double[] ttSumPerHourMode = new double[24];

		TripAgg(String modeFilter) {
			this.modeFilter = (modeFilter == null || modeFilter.isBlank()) ? null : modeFilter;
		}

		@Override
		public void handleEvent(PersonDepartureEvent e) {
			depMap.put(e.getPersonId(), new Dep(e.getTime(), e.getLegMode()));
		}

		@Override
		public void handleEvent(PersonArrivalEvent e) {
			Dep dep = depMap.remove(e.getPersonId());
			if (dep != null) {
				double tt = Math.max(0, e.getTime() - dep.t);
				tripsAll++; ttSumAll += tt;

				int hour = Math.min(23, Math.max(0, (int)Math.floor(dep.t / 3600.0)));
				tripsPerHourAll[hour]++; ttSumPerHourAll[hour] += tt;

				if (modeFilter != null && modeFilter.equals(dep.mode)) {
					tripsMode++; ttSumMode += tt;
					tripsPerHourMode[hour]++; ttSumPerHourMode[hour] += tt;
				}
			}
		}

		@Override public void reset(int iteration) { }

		double avgTripTimeAll()  { return tripsAll  > 0 ? ttSumAll  / tripsAll  : Double.NaN; }
		double avgTripTimeMode() { return tripsMode > 0 ? ttSumMode / tripsMode : Double.NaN; }
	}
}
